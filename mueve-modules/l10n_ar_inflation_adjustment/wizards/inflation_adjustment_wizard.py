# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang, format_date
from dateutil.relativedelta import relativedelta


class InflationAdjustmentWizard(models.TransientModel):
    """
    Wizard para generar el asiento de ajuste por inflación contable.
    
    Este wizard implementa el cálculo del ajuste por inflación según la
    normativa argentina (RT 6, RT 17, RT 48) aplicable al cierre del
    ejercicio fiscal.
    
    El ajuste se realiza sobre las cuentas marcadas con el tag "Non Monetary",
    que representan rubros no monetarios como:
    - Bienes de uso (activos fijos)
    - Inversiones permanentes
    - Patrimonio neto
    - Resultados del ejercicio
    - Inventarios (cuando aplica)
    """

    _name = 'inflation.adjustment.wizard'
    _description = 'Wizard de Ajuste por Inflación'

    # === Campos de configuración del período ===
    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        help='Fecha de inicio del ejercicio fiscal a ajustar.'
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        help='Fecha de cierre del ejercicio fiscal.'
    )
    
    # === Campos de la compañía ===
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Moneda',
    )
    
    # === Campos del asiento ===
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        domain="[('type', '=', 'general')]", check_company=True,
        required=True,
        help='Diario contable donde se registrará el asiento de ajuste.'
    )
    result_account_id = fields.Many2one(
        'account.account',
        string='Cuenta de Resultado por Ajuste',
        domain="[('deprecated', '=', False)]", check_company=True,
        required=True,
        help='Cuenta donde se registrará el resultado neto del ajuste por inflación. '
             'Generalmente es una cuenta de resultados financieros '
             '(RECPAM - Resultado por Exposición a los Cambios en el Poder Adquisitivo de la Moneda).'
    )
    
    # === Campos de índices ===
    start_index_id = fields.Many2one(
        'inflation.adjustment.index',
        string='Índice Inicial',
        compute='_compute_indices',
        store=True,
    )
    start_index = fields.Float(
        string='Valor Índice Inicial',
        compute='_compute_indices',
        store=True,
        digits=(12, 4),
    )
    end_index_id = fields.Many2one(
        'inflation.adjustment.index',
        string='Índice Final',
        compute='_compute_indices',
        store=True,
    )
    end_index = fields.Float(
        string='Valor Índice Final',
        compute='_compute_indices',
        store=True,
        digits=(12, 4),
    )
    adjustment_factor = fields.Float(
        string='Factor de Ajuste Total (%)',
        compute='_compute_indices',
        store=True,
        digits=(8, 4),
        help='Factor de ajuste total del período = (Índice Final / Índice Inicial - 1) * 100'
    )
    
    # === Campos para asientos de cierre/apertura ===
    has_closure_entries = fields.Selection(
        selection=[
            ('no', 'No'),
            ('yes', 'Sí'),
        ],
        string='¿Ha realizado asientos de cierre/apertura?',
        default='no',
        help='Si ha realizado asientos de cierre y apertura del ejercicio anterior, '
             'debe indicarlos para excluirlos del cálculo del ajuste.'
    )
    closure_move_id = fields.Many2one(
        'account.move',
        string='Asiento de Cierre',
        domain="[('company_id', '=', company_id), ('state', '=', 'posted')]",
        help='Asiento de cierre del ejercicio anterior a excluir del cálculo.'
    )
    opening_move_id = fields.Many2one(
        'account.move',
        string='Asiento de Apertura',
        domain="[('company_id', '=', company_id), ('state', '=', 'posted')]",
        help='Asiento de apertura del ejercicio a excluir del cálculo.'
    )
    
    # === Campos informativos ===
    warning_message = fields.Text(
        string='Advertencias',
        compute='_compute_warnings',
    )
    
    # === Campos para preview ===
    preview_line_ids = fields.One2many(
        'inflation.adjustment.wizard.line',
        'wizard_id',
        string='Líneas de Ajuste (Preview)',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('preview', 'Vista Previa'),
            ('done', 'Confirmado'),
        ],
        string='Estado',
        default='draft',
    )

    @api.model
    def default_get(self, field_list):
        """Establece valores por defecto basados en el ejercicio fiscal."""
        res = super().default_get(field_list)
        
        today = fields.Date.today()
        company = self.env.company
        
        # Calcular fechas del ejercicio fiscal anterior
        try:
            # Intentar obtener el ejercicio fiscal del año anterior
            fiscal_dates = company.compute_fiscalyear_dates(
                today - relativedelta(years=1)
            )
            res['date_from'] = fiscal_dates.get('date_from')
            res['date_to'] = fiscal_dates.get('date_to')
        except Exception:
            # Si falla, usar el año calendario anterior
            res['date_from'] = today.replace(month=1, day=1) - relativedelta(years=1)
            res['date_to'] = today.replace(month=12, day=31) - relativedelta(years=1)
        
        res['company_id'] = company.id
        
        # Buscar diario de ajuste por inflación o diario misceláneo
        journal = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
            '|',
            ('name', 'ilike', 'inflación'),
            ('name', 'ilike', 'ajuste'),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'general'),
            ], limit=1)
        if journal:
            res['journal_id'] = journal.id
        
        return res

    @api.depends('date_from', 'date_to')
    def _compute_indices(self):
        """Calcula los índices de inicio y fin del período."""
        IndexModel = self.env['inflation.adjustment.index']
        
        for wizard in self:
            wizard.start_index_id = False
            wizard.start_index = 0.0
            wizard.end_index_id = False
            wizard.end_index = 0.0
            wizard.adjustment_factor = 0.0
            
            if wizard.date_from:
                start_idx = IndexModel.find(wizard.date_from)
                wizard.start_index_id = start_idx
                wizard.start_index = start_idx.value if start_idx else 0.0
            
            if wizard.date_to:
                end_idx = IndexModel.find(wizard.date_to)
                wizard.end_index_id = end_idx
                wizard.end_index = end_idx.value if end_idx else 0.0
            
            if wizard.start_index and wizard.end_index:
                wizard.adjustment_factor = (
                    (wizard.end_index / wizard.start_index) - 1
                ) * 100

    @api.depends('date_from', 'date_to', 'start_index', 'end_index')
    def _compute_warnings(self):
        """Genera advertencias sobre datos faltantes o inconsistencias."""
        for wizard in self:
            warnings = []
            
            if wizard.date_from and not wizard.start_index:
                warnings.append(_(
                    '⚠ No se encontró índice IPC para la fecha de inicio (%s). '
                    'Por favor, cargue el índice correspondiente.'
                ) % wizard.date_from)
            
            if wizard.date_to and not wizard.end_index:
                warnings.append(_(
                    '⚠ No se encontró índice IPC para la fecha de fin (%s). '
                    'Por favor, cargue el índice correspondiente.'
                ) % wizard.date_to)
            
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    warnings.append(_(
                        '⚠ La fecha de inicio no puede ser posterior a la fecha de fin.'
                    ))
                
                # Verificar que existan todos los índices intermedios
                if wizard.start_index and wizard.end_index:
                    missing = self._check_missing_indices(wizard.date_from, wizard.date_to)
                    if missing:
                        warnings.append(_(
                            '⚠ Faltan índices IPC para los siguientes períodos: %s'
                        ) % ', '.join(missing))
            
            wizard.warning_message = '\n'.join(warnings) if warnings else False

    def _check_missing_indices(self, date_from, date_to):
        """Verifica si faltan índices en el período y retorna lista de faltantes."""
        IndexModel = self.env['inflation.adjustment.index']
        missing = []
        
        current = date_from.replace(day=1)
        end = date_to.replace(day=1)
        
        while current <= end:
            if not IndexModel.find(current):
                missing.append(current.strftime('%m/%Y'))
            current += relativedelta(months=1)
        
        return missing

    def _get_move_line_domain(self):
        """
        Construye el dominio para buscar los apuntes contables a ajustar.
        
        Criterios:
        - Cuentas con tag "No Monetaria" (no monetarias)
        - De la compañía seleccionada
        - Asientos publicados
        - Excluye asientos de cierre/apertura si se especifican
        """
        self.ensure_one()
        
        # Obtener el tag de cuentas no monetarias usando el método del modelo account.account
        non_monetary_tag = self.env['account.account']._get_non_monetary_tag()
        
        if not non_monetary_tag:
            raise UserError(_(
                'No se encontró el tag "No Monetaria". '
                'Verifique que el módulo esté correctamente instalado.'
            ))
        
        domain = [
            ('account_id.tag_ids', 'in', non_monetary_tag.id),
            ('company_id', '=', self.company_id.id),
            ('move_id.state', '=', 'posted'),
            ('parent_state', '=', 'posted'),
        ]
        
        # Excluir asientos de cierre/apertura
        if self.has_closure_entries == 'yes':
            if self.closure_move_id:
                domain.append(('move_id', '!=', self.closure_move_id.id))
            if self.opening_move_id:
                domain.append(('move_id', '!=', self.opening_move_id.id))
        
        return domain

    def _get_periods(self):
        """
        Genera la lista de períodos mensuales con sus índices y factores.
        
        :return: Lista de diccionarios con:
            - date_from: primer día del mes
            - date_to: último día del mes
            - index: recordset del índice
            - factor: factor de ajuste para ese mes
        """
        self.ensure_one()
        
        if not self.date_from or not self.date_to:
            raise UserError(_('Por favor indique el rango de fechas.'))
        
        if not self.end_index:
            raise UserError(_(
                'No se encontró el índice IPC para la fecha de cierre (%s).'
            ) % self.date_to)
        
        IndexModel = self.env['inflation.adjustment.index']
        periods = []
        
        current = self.date_from.replace(day=1)
        end = self.date_to
        
        while current <= end:
            # Último día del mes
            month_end = current + relativedelta(months=1, days=-1)
            if month_end > end:
                month_end = end
            
            # Buscar índice del mes
            index = IndexModel.find(current, raise_if_not_found=True)
            
            periods.append({
                'date_from': current,
                'date_to': month_end,
                'index': index,
                'factor': (self.end_index / index.value) - 1.0,
            })
            
            current += relativedelta(months=1)
        
        return periods

    def _calculate_initial_balance_adjustment(self):
        """
        Calcula el ajuste por inflación para los saldos iniciales.
        
        Para cuentas con saldo inicial (aquellas que incluyen saldo inicial
        en balance), se ajusta el saldo existente al inicio del período
        usando el factor del período anterior.
        
        :return: Lista de diccionarios con datos de líneas de ajuste
        """
        self.ensure_one()
        
        lines_data = []
        MoveLine = self.env['account.move.line']
        IndexModel = self.env['inflation.adjustment.index']
        
        # Obtener índice del mes anterior al inicio
        prev_month = self.date_from + relativedelta(months=-1)
        prev_index = IndexModel.find(prev_month)
        
        if not prev_index:
            # Si no hay índice del mes anterior, no ajustamos saldos iniciales
            return lines_data
        
        initial_factor = (self.end_index / prev_index.value) - 1.0
        
        # Dominio para saldos iniciales (movimientos anteriores al período)
        domain = self._get_move_line_domain()
        domain += [
            ('account_id.include_initial_balance', '=', True),
            ('date', '<', self.date_from),
        ]
        
        # Agrupar por cuenta
        grouped = MoveLine.read_group(
            domain,
            ['account_id', 'balance'],
            ['account_id'],
        )
        
        for group in grouped:
            balance = group.get('balance', 0.0)
            adjustment = balance * initial_factor
            
            if self.currency_id.is_zero(adjustment):
                continue
            
            adjustment = self.currency_id.round(adjustment)
            account_id = group.get('account_id')[0]
            account = self.env['account.account'].browse(account_id)
            
            lines_data.append({
                'account_id': account_id,
                'account_name': account.display_name,
                'period': _('Saldo Inicial (antes de %s)') % format_date(
                    self.env, self.date_from, date_format='MM/yyyy'
                ),
                'original_balance': balance,
                'factor': initial_factor * 100,
                'adjustment_amount': adjustment,
                'is_initial': True,
            })
        
        return lines_data

    def _calculate_period_adjustments(self):
        """
        Calcula el ajuste por inflación para cada período mensual.
        
        :return: Lista de diccionarios con datos de líneas de ajuste
        """
        self.ensure_one()
        
        lines_data = []
        MoveLine = self.env['account.move.line']
        
        periods = self._get_periods()
        
        for period in periods:
            # Dominio para movimientos del período
            domain = self._get_move_line_domain()
            domain += [
                ('date', '>=', period['date_from']),
                ('date', '<=', period['date_to']),
            ]
            
            # Agrupar por cuenta
            grouped = MoveLine.read_group(
                domain,
                ['account_id', 'balance'],
                ['account_id'],
            )
            
            for group in grouped:
                balance = group.get('balance', 0.0)
                adjustment = balance * period['factor']
                
                if self.currency_id.is_zero(adjustment):
                    continue
                
                adjustment = self.currency_id.round(adjustment)
                account_id = group.get('account_id')[0]
                account = self.env['account.account'].browse(account_id)
                
                lines_data.append({
                    'account_id': account_id,
                    'account_name': account.display_name,
                    'period': format_date(
                        self.env, period['date_from'], date_format='MM/yyyy'
                    ),
                    'original_balance': balance,
                    'factor': period['factor'] * 100,
                    'adjustment_amount': adjustment,
                    'is_initial': False,
                })
        
        return lines_data

    def action_preview(self):
        """
        Genera una vista previa de las líneas de ajuste.
        """
        self.ensure_one()
        
        # Limpiar líneas anteriores
        self.preview_line_ids.unlink()
        
        # Calcular ajustes
        all_lines = []
        all_lines.extend(self._calculate_initial_balance_adjustment())
        all_lines.extend(self._calculate_period_adjustments())
        
        if not all_lines:
            raise UserError(_(
                'No se encontraron movimientos contables para ajustar '
                'en el período seleccionado. Verifique que existan cuentas '
                'con el tag "Non Monetary" y movimientos publicados.'
            ))
        
        # Crear líneas de preview
        PreviewLine = self.env['inflation.adjustment.wizard.line']
        for line in all_lines:
            PreviewLine.create({
                'wizard_id': self.id,
                'account_id': line['account_id'],
                'period': line['period'],
                'original_balance': line['original_balance'],
                'factor': line['factor'],
                'adjustment_amount': line['adjustment_amount'],
                'is_initial': line.get('is_initial', False),
            })
        
        self.state = 'preview'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_back_to_draft(self):
        """Vuelve al estado borrador."""
        self.ensure_one()
        self.preview_line_ids.unlink()
        self.state = 'draft'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        """
        Confirma y genera el asiento de ajuste por inflación.
        
        Crea un asiento contable con:
        - Una línea por cada cuenta ajustada (debe o haber según ajuste)
        - Una línea de contrapartida en la cuenta de resultado por ajuste
        """
        self.ensure_one()
        
        # Validaciones
        if not self.journal_id:
            raise UserError(_('Debe seleccionar un diario contable.'))
        if not self.result_account_id:
            raise UserError(_('Debe seleccionar la cuenta de resultado por ajuste.'))
        
        # Usar líneas de preview si existen, sino calcular
        if self.preview_line_ids:
            lines_data = [{
                'account_id': line.account_id.id,
                'period': line.period,
                'original_balance': line.original_balance,
                'factor': line.factor,
                'adjustment_amount': line.adjustment_amount,
            } for line in self.preview_line_ids]
        else:
            lines_data = []
            lines_data.extend(self._calculate_initial_balance_adjustment())
            lines_data.extend(self._calculate_period_adjustments())
        
        if not lines_data:
            raise UserError(_(
                'No hay líneas de ajuste para procesar.'
            ))
        
        # Preparar líneas del asiento
        move_lines = []
        total_debit = 0.0
        total_credit = 0.0
        
        for line in lines_data:
            amount = line['adjustment_amount']
            if self.currency_id.is_zero(amount):
                continue
            
            name = _('Ajuste por inflación %s (%s * %.2f%%)') % (
                line['period'],
                formatLang(self.env, line['original_balance'], currency_obj=self.currency_id),
                line['factor'],
            )
            
            move_lines.append({
                'account_id': line['account_id'],
                'name': name,
                'debit': amount if amount > 0 else 0.0,
                'credit': -amount if amount < 0 else 0.0,
            })
            
            if amount > 0:
                total_debit += amount
            else:
                total_credit += -amount
        
        # Línea de contrapartida (RECPAM)
        balance = total_debit - total_credit
        if not self.currency_id.is_zero(balance):
            move_lines.append({
                'account_id': self.result_account_id.id,
                'name': _('Resultado por Exposición a la Inflación (RECPAM) [%s - %s]') % (
                    self.date_from, self.date_to
                ),
                'debit': -balance if balance < 0 else 0.0,
                'credit': balance if balance > 0 else 0.0,
            })
        
        # Crear asiento
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': _('Ajuste por Inflación - Ejercicio %s') % self.date_to.year,
            'line_ids': [(0, 0, vals) for vals in move_lines],
        }
        
        move = self.env['account.move'].create(move_vals)
        
        self.state = 'done'
        
        # Retornar acción para ver el asiento creado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }


class InflationAdjustmentWizardLine(models.TransientModel):
    """Líneas de preview para el wizard de ajuste por inflación."""

    _name = 'inflation.adjustment.wizard.line'
    _description = 'Línea de Ajuste por Inflación (Preview)'

    wizard_id = fields.Many2one(
        'inflation.adjustment.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta',
        required=True,
    )
    period = fields.Char(
        string='Período',
    )
    original_balance = fields.Monetary(
        string='Saldo Original',
        currency_field='currency_id',
    )
    factor = fields.Float(
        string='Factor (%)',
        digits=(8, 4),
    )
    adjustment_amount = fields.Monetary(
        string='Importe Ajuste',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='wizard_id.currency_id',
    )
    is_initial = fields.Boolean(
        string='Es Saldo Inicial',
        default=False,
    )
