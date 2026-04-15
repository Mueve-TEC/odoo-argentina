from odoo import models


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_upgrade(self, *args, **kwargs):
        """
        Override to fix TypeError in Odoo 16.0.
        The original method doesn't accept any arguments, but the frontend
        sometimes calls it with an extra positional argument.
        This wrapper accepts and ignores any extra arguments.
        """
        return super(IrModuleModule, self).button_immediate_upgrade()
