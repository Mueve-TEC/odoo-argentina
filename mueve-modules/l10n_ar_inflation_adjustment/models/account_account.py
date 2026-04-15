# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountAccount(models.Model):
    """
    Extensión del modelo account.account para agregar funcionalidad
    relacionada con el ajuste por inflación.
    """

    _inherit = 'account.account'

    inflation_adjustable = fields.Boolean(
        string='Ajustable por Inflación',
        compute='_compute_inflation_adjustable',
        store=True,
        help='Indica si la cuenta es ajustable por inflación. '
             'Se determina automáticamente según el tag "No Monetaria" '
             'asignado a la cuenta.'
    )

    # Tipos de cuenta que por defecto son no monetarias (ajustables por inflación)
    NON_MONETARY_ACCOUNT_TYPES = [
        'asset_non_current',
        'asset_fixed',
        'income',
        'income_other',
        'expense',
        'expense_depreciation',
        'equity',
        'expense_direct_cost',
    ]

    def _get_non_monetary_tag(self):
        """
        Obtiene el tag de cuenta no monetaria.
        Busca primero el tag propio del módulo, luego el de l10n_ar_ux por compatibilidad.
        """
        # Primero intentar con el tag propio de este módulo
        tag = self.env.ref(
            'l10n_ar_inflation_adjustment.non_monetary_account_tag',
            raise_if_not_found=False
        )
        if tag:
            return tag
        
        # Fallback al tag de l10n_ar_ux si existe (para compatibilidad)
        tag = self.env.ref(
            'l10n_ar_ux.no_monetaria_tag',
            raise_if_not_found=False
        )
        return tag

    @api.depends('tag_ids')
    def _compute_inflation_adjustable(self):
        """
        Calcula si la cuenta es ajustable por inflación basándose en
        si tiene el tag "No Monetaria".
        
        Según la RT 6 y RT 17, las cuentas no monetarias son las que
        deben ajustarse por inflación (activos fijos, inventarios,
        patrimonio neto, resultados, etc.).
        """
        non_monetary_tag = self._get_non_monetary_tag()
        
        for account in self:
            if non_monetary_tag:
                account.inflation_adjustable = non_monetary_tag.id in account.tag_ids.ids
            else:
                # Si no existe el tag, usar tipos de cuenta por defecto
                account.inflation_adjustable = account.account_type in self.NON_MONETARY_ACCOUNT_TYPES

    @api.model
    def set_non_monetary_tag(self, company=None):
        """
        Asigna el tag "No Monetaria" a las cuentas correspondientes
        según su tipo de cuenta.
        
        Este método puede ejecutarse manualmente o mediante una acción
        planificada para mantener actualizadas las cuentas.
        
        :param company: Compañía(s) para las cuales asignar el tag.
                       Si no se especifica, usa la compañía actual.
        """
        if company is None:
            company = self.env.company
        
        non_monetary_tag = self._get_non_monetary_tag()
        if not non_monetary_tag:
            return False
        
        # Buscar cuentas que deberían tener el tag pero no lo tienen
        accounts = self.search([
            ('account_type', 'in', self.NON_MONETARY_ACCOUNT_TYPES),
            ('company_ids', 'in', company.ids if hasattr(company, 'ids') else [company.id]),
            ('tag_ids', 'not in', [non_monetary_tag.id]),
        ])
        
        if accounts:
            accounts.write({'tag_ids': [(4, non_monetary_tag.id)]})
        
        return True

    @api.model
    def get_inflation_adjustable_accounts(self, company_id=None):
        """
        Obtiene todas las cuentas ajustables por inflación.
        
        :param company_id: ID de la compañía (opcional)
        :return: recordset de cuentas ajustables
        """
        domain = [('inflation_adjustable', '=', True)]
        if company_id:
            domain.append(('company_ids', '=', company_id))
        return self.search(domain)

    @api.model
    def get_non_monetary_tag_id(self):
        """
        Devuelve el ID del tag de cuenta no monetaria.
        Útil para usar en dominios de búsqueda.
        """
        tag = self._get_non_monetary_tag()
        return tag.id if tag else False
