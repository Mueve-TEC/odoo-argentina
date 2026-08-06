"""Tests for the FE 'Check rate' currency-rate lookup."""

from unittest.mock import patch

from odoo.addons.l10n_ar_fiscal_ws.models.arcaws import ArcaWsMethod
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws_fe")
class TestCurrencyRate(TransactionCase):
    """Regression for commit 44a05d857: 'Check rate' button must dispatch the
    currency-rate lookup through the arcaws.method mechanism."""

    @classmethod
    def setUpClass(cls):
        """Reuse the AR sale journal and bind it to the wsfe arcaws service."""
        super().setUpClass()
        cls.journal = cls.env["account.journal"].search([("type", "=", "sale")], limit=1)
        cls.journal.l10n_ar_afip_pos_system = "RAW_MAW"
        cls.arcaws = cls.journal.arcaws
        cls.arcaws.ensure_one()
        cls.currency_rate_method = cls.arcaws.method_ids.filtered(lambda m: m.name == "get_currency_rate")
        cls.currency_rate_method.ensure_one()

    def test_currency_rate_updates_invoice(self):
        """A mocked rate must set invoice_currency_rate = 1 / rate."""
        invoice = self.env["account.move"].create({"move_type": "out_invoice", "journal_id": self.journal.id})
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=820.5):
            invoice.get_pyafipws_currency_rate()
        self.assertAlmostEqual(invoice.invoice_currency_rate, 1 / 820.5)

    def test_currency_rate_no_rate_raises_user_error(self):
        """ARCA returning no ResultGet/MonCotiz must not crash (RPC 500)."""
        invoice = self.env["account.move"].create({"move_type": "out_invoice", "journal_id": self.journal.id})
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=False):
            with self.assertRaises(UserError):
                invoice.get_pyafipws_currency_rate()
