# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class InflationAdjustmentIndex(models.Model):
    """
    Modelo para almacenar los índices de precios al consumidor (IPC) publicados
    por el INDEC. Estos índices se utilizan para calcular el ajuste por inflación
    contable requerido por la normativa argentina (RT 6, RT 17).

    El índice IPC se publica mensualmente y representa el nivel general de precios.
    Para el ajuste por inflación, se utiliza la relación entre el índice del mes
    de cierre y el índice del mes de origen de cada partida.
    """

    _name = 'inflation.adjustment.index'
    _description = 'Índice de Ajuste por Inflación (IPC INDEC)'
    _order = 'date desc'
    _rec_name = 'date'

    date = fields.Date(string='Fecha', required=True, help='Primer día del mes al que corresponde el índice IPC.')
    value = fields.Float(
        string='Valor IPC',
        required=True,
        digits=(12, 4),
        help='Valor del Índice de Precios al Consumidor (IPC) publicado por INDEC.',
    )
    xml_id = fields.Char(
        compute='_compute_xml_id',
        string='ID Externo',
        help='Identificador externo del registro para referencia en XML.',
    )
    variation = fields.Float(
        string='Variación Mensual (%)',
        compute='_compute_variation',
        digits=(6, 2),
        help='Variación porcentual respecto al mes anterior.',
    )
    annual_variation = fields.Float(
        string='Variación Interanual (%)',
        compute='_compute_variation',
        digits=(6, 2),
        help='Variación porcentual respecto al mismo mes del año anterior.',
    )

    @api.depends('date', 'value')
    def _compute_variation(self):
        """Calcula las variaciones mensual e interanual del índice."""
        for rec in self:
            rec.variation = 0.0
            rec.annual_variation = 0.0
            if rec.date and rec.value:
                # Variación mensual
                prev_month = rec.date + relativedelta(months=-1)
                prev_index = self.search([('date', '>=', prev_month), ('date', '<', rec.date)], limit=1)
                if prev_index and prev_index.value:
                    rec.variation = ((rec.value / prev_index.value) - 1) * 100

                # Variación interanual
                prev_year = rec.date + relativedelta(years=-1)
                prev_year_index = self.find(prev_year)
                if prev_year_index and prev_year_index.value:
                    rec.annual_variation = ((rec.value / prev_year_index.value) - 1) * 100

    @api.depends()
    def _compute_xml_id(self):
        """Obtiene el ID externo del registro."""
        res = self.get_external_id()
        for record in self:
            record.xml_id = res.get(record.id)

    @api.model
    def find(self, date, raise_if_not_found=False):
        """
        Busca el índice correspondiente a un período (mes/año).

        :param date: Fecha para la cual buscar el índice
        :param raise_if_not_found: Si es True, lanza error si no encuentra índice
        :return: recordset del índice encontrado (vacío si no existe)
        """
        if not date:
            return self.browse()

        date_range = self._get_period_dates_from_date(date)
        index = self.search(
            [
                ('date', '>=', date_range.get('date_from')),
                ('date', '<=', date_range.get('date_to')),
            ],
            limit=1,
        )

        if not index and raise_if_not_found:
            date_obj = fields.Date.from_string(date) if isinstance(date, str) else date
            raise ValidationError(
                _(
                    'No se encontró el índice de inflación para el período %s/%s. '
                    'Por favor, cargue el índice IPC correspondiente.'
                )
                % (date_obj.strftime("%m"), date_obj.year)
            )

        return index

    @api.model
    def _get_period_dates_from_date(self, date):
        """
        Obtiene las fechas de inicio y fin del período (mes) para una fecha dada.
        Este es un método de modelo que no depende de self.

        :param date: Fecha base
        :return: dict con 'date_from' y 'date_to'
        """
        if isinstance(date, str):
            date = fields.Date.from_string(date)

        date_from = date.replace(day=1)
        date_to = date_from + relativedelta(months=1, days=-1)

        return {
            'date_from': date_from,
            'date_to': date_to,
        }

    def _get_period_dates(self, date=None):
        """
        Obtiene las fechas de inicio y fin del período (mes) para una fecha dada.

        :param date: Fecha base (si no se proporciona, usa la fecha del registro)
        :return: dict con 'date_from' y 'date_to'
        """
        if date:
            return self._get_period_dates_from_date(date)

        self.ensure_one()
        return self._get_period_dates_from_date(self.date)

    @api.constrains('date')
    def _check_date_unique(self):
        """Verifica que solo exista un índice por período (mes)."""
        for rec in self:
            existing = self.find(rec.date)
            if len(existing) > 1 or (existing and existing.id != rec.id):
                date_obj = fields.Date.from_string(rec.date) if isinstance(rec.date, str) else rec.date
                raise ValidationError(
                    _(
                        'Ya existe un índice para el período %s/%s. '
                        'Solo puede existir un índice de inflación por mes.'
                    )
                    % (date_obj.strftime("%m"), date_obj.year)
                )

    @api.constrains('date')
    def _check_first_day_of_month(self):
        """Verifica que la fecha sea el primer día del mes."""
        for rec in self:
            date_obj = fields.Date.from_string(rec.date) if isinstance(rec.date, str) else rec.date
            if date_obj.day != 1:
                raise ValidationError(
                    _('El índice debe corresponder al primer día de cada mes. ' 'Fecha ingresada: %s') % rec.date
                )

    @api.constrains('value')
    def _check_positive_value(self):
        """Verifica que el valor del índice sea positivo."""
        for rec in self:
            if rec.value <= 0:
                raise ValidationError(_('El valor del índice IPC debe ser un número positivo.'))

    @api.model
    def _create_xml_id(self, record):
        """
        Crea un xml_id para el registro si no existe.
        Útil para cuando se crean índices manualmente.
        """
        if record.xml_id:
            return

        date_obj = fields.Date.from_string(record.date) if isinstance(record.date, str) else record.date
        xml_id_name = 'index_%02d_%s' % (date_obj.month, date_obj.year)

        existing = self.env['ir.model.data'].search(
            [
                ('module', '=', 'l10n_ar_inflation_adjustment'),
                ('name', '=', xml_id_name),
            ]
        )
        if existing:
            return

        self.env['ir.model.data'].create(
            {
                'name': xml_id_name,
                'model': self._name,
                'module': 'l10n_ar_inflation_adjustment',
                'res_id': record.id,
                'noupdate': True,
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Override para crear xml_id automáticamente."""
        records = super().create(vals_list)
        # Solo crear xml_id si no estamos en modo instalación
        if not self.env.context.get('install_mode', False):
            for record in records:
                self._create_xml_id(record)
        return records

    def get_factor(self, end_index_value):
        """
        Calcula el factor de ajuste entre este índice y un índice final.

        :param end_index_value: Valor del índice de cierre
        :return: Factor de ajuste (end_index / this_index - 1)
        """
        self.ensure_one()
        if not self.value:
            raise ValidationError(_('El índice no tiene valor asignado.'))
        return (end_index_value / self.value) - 1.0

    @api.model
    def get_indices_for_period(self, date_from, date_to):
        """
        Obtiene todos los índices para un rango de fechas.

        :param date_from: Fecha inicial del período
        :param date_to: Fecha final del período
        :return: recordset con los índices ordenados por fecha
        """
        return self.search(
            [
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ],
            order='date',
        )
