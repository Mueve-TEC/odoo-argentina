"""Argentina-specific options for the Point of Sale configuration."""

from odoo import api, fields, models


class PosConfig(models.Model):
    """Add the "invoice by default" option to the POS configuration."""

    _inherit = "pos.config"

    l10n_ar_default_to_invoice = fields.Boolean(
        string="Invoice by default",
        default=True,
        help="If enabled, new orders are marked as 'To invoice' by default. "
        "The cashier can still turn the toggle off on the payment screen.",
    )

    @api.depends(
        # Mirror of core's depends on _compute_local_data_integrity
        # (point_of_sale/models/pos_config.py) plus our field: re-declaring
        # @api.depends on an inherited compute replaces the whole list, so
        # core's triggers must be repeated here.
        "use_pricelist",
        "pricelist_id",
        "available_pricelist_ids",
        "payment_method_ids",
        "limit_categories",
        "iface_available_categ_ids",
        "module_pos_hr",
        "module_pos_discount",
        "iface_tipproduct",
        "default_preset_id",
        "module_pos_appointment",
        "cash_rounding",
        "rounding_method",
        "only_round_cash_method",
        "l10n_ar_default_to_invoice",
    )
    def _compute_local_data_integrity(self):
        # Bump ``last_data_change`` when this option changes: the POS uses it
        # to decide whether it must reload the configuration from the server
        # (otherwise the cached value is kept and the setting seems ignored).
        return super()._compute_local_data_integrity()
