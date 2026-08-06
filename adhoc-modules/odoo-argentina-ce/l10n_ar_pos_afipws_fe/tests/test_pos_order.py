"""Tests for the ARCA electronic-invoice POS refund linking."""

# pylint: disable=invalid-name,protected-access

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosOrderPrepareInvoiceVals(TransactionCase):
    """Test the reversed_entry_id logic on POS refunds."""

    @classmethod
    def setUpClass(cls):
        """Set up an AR company, a RAW_MAW journal and a POS session."""
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar").id
        cls.journal = cls.env["account.journal"].search([("type", "=", "sale")], limit=1)
        cls.journal.l10n_ar_afip_pos_system = "RAW_MAW"
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Pos Customer",
                "country_id": cls.company.country_id.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "list_price": 100,
                "sale_ok": True,
            }
        )
        picking_type = cls.env["stock.picking.type"].search(
            [
                ("code", "=", "outgoing"),
                ("warehouse_id.company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.config = cls.env["pos.config"].create(
            {
                "name": "Test POS",
                "journal_id": cls.journal.id,
                "invoice_journal_id": cls.journal.id,
                "picking_type_id": picking_type.id,
                "iface_tax_included": "total",
                "picking_policy": "direct",
            }
        )
        cls.session = cls.env["pos.session"].create(
            {
                "config_id": cls.config.id,
                "user_id": cls.env.user.id,
            }
        )

    def _create_sale_order(self):
        """Create a sale POS order with one line."""
        return self.env["pos.order"].create(
            {
                "name": "/",
                "partner_id": self.partner.id,
                "session_id": self.session.id,
                "amount_tax": 0,
                "amount_total": 100,
                "amount_paid": 100,
                "amount_return": 0,
                "date_order": fields.Datetime.now(),
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Product",
                            "product_id": self.product.id,
                            "qty": 1,
                            "price_unit": 100,
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    )
                ],
            }
        )

    def _create_refund_order(self, order):
        """Create a refund POS order linked to the given order."""
        return self.env["pos.order"].create(
            {
                "name": "/",
                "partner_id": self.partner.id,
                "session_id": self.session.id,
                "amount_tax": 0,
                "amount_total": -100,
                "amount_paid": -100,
                "amount_return": 0,
                "date_order": fields.Datetime.now(),
                "lines": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Product",
                            "product_id": self.product.id,
                            "qty": -1,
                            "price_unit": 100,
                            "price_subtotal": -100,
                            "price_subtotal_incl": -100,
                            "refunded_orderline_id": order.lines[0].id,
                        },
                    )
                ],
            }
        )

    def _create_invoice(self, order, **kwargs):
        """Create an invoice and attach it to the given order."""
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_date": fields.Date.today(),
        }
        vals.update(kwargs)
        move = self.env["account.move"].create(vals)
        order.account_move = move.id
        return move

    def test_refund_links_arca_invoice(self):
        """Refund of an ARCA-authorized invoice links the reversal."""
        order = self._create_sale_order()
        invoice = self._create_invoice(order, afip_auth_code="68448767638166")
        self.assertTrue(order.config_id.invoice_journal_id.arcaws)
        refund = self._create_refund_order(order)
        vals = refund._prepare_invoice_vals()
        self.assertEqual(vals["move_type"], "out_refund")
        self.assertEqual(vals["reversed_entry_id"], invoice.id)

    def test_refund_without_invoice_has_no_reversal(self):
        """Refund of an uninvoiced order has no reversal link."""
        order = self._create_sale_order()
        refund = self._create_refund_order(order)
        vals = refund._prepare_invoice_vals()
        self.assertEqual(vals["move_type"], "out_refund")
        self.assertNotIn("reversed_entry_id", vals)

    def test_refund_non_arca_invoice_does_not_raise(self):
        """Refund of a non-ARCA invoice is not blocked."""
        order = self._create_sale_order()
        invoice = self._create_invoice(order)
        self.assertFalse(invoice.afip_auth_code)
        refund = self._create_refund_order(order)
        vals = refund._prepare_invoice_vals()
        self.assertEqual(vals["reversed_entry_id"], invoice.id)
