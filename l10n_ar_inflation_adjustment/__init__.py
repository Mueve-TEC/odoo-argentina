# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from . import models
from . import wizards


def post_init_hook(cr, registry):
    """
    Hook ejecutado después de la instalación del módulo.
    Asigna automáticamente el tag "No Monetaria" a las cuentas correspondientes.
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Asignar tag a cuentas de todas las compañías argentinas
    companies = env['res.company'].search([
        ('country_id.code', '=', 'AR')
    ])
    
    if companies:
        env['account.account'].set_non_monetary_tag(companies)
