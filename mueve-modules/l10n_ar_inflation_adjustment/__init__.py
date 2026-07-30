# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from . import models, wizards


def post_init_hook(env):
    """
    Hook ejecutado después de la instalación del módulo.
    Asigna automáticamente el tag "No Monetaria" a las cuentas correspondientes.
    """
    # Asignar tag a cuentas de todas las compañías argentinas
    companies = env['res.company'].search([('country_id.code', '=', 'AR')])

    if companies:
        env['account.account'].set_non_monetary_tag(companies)
