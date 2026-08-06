"""Link POS refunds to the original ARCA electronic invoice."""

from odoo import _, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    """Link POS refunds to their original ARCA electronic invoice."""

    # pylint: disable=too-few-public-methods
    _inherit = "pos.order"

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        invoice_ids = self.refunded_order_id.mapped("account_move").filtered(
            lambda x: x.company_id.country_id.code == "AR"
            and x.is_invoice()
            and x.move_type in ["out_invoice"]
            and x.journal_id.arcaws
            and x.afip_auth_code
        )
        if len(invoice_ids) > 1:
            raise UserError(_("Only can refund one invoice at a time"))
        if len(invoice_ids) == 1:
            vals["reversed_entry_id"] = invoice_ids[0].id
        return vals
