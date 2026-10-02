"""Expose the POS "invoice by default" option in the settings."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Add the POS "invoice by default" option to the settings form."""

    _inherit = "res.config.settings"

    pos_l10n_ar_default_to_invoice = fields.Boolean(
        related="pos_config_id.l10n_ar_default_to_invoice",
        readonly=False,
    )
