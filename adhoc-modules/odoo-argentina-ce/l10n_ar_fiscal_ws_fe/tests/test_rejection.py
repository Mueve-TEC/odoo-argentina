"""Tests for ARCA rejection diagnostics persistence (PR #104 port, W3)."""

from unittest.mock import patch

from odoo.addons.l10n_ar_fiscal_ws.models.arcaws import ArcaWsMethod
from odoo.addons.l10n_ar_fiscal_ws.models.res_company import ResCompany
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws_fe")
class TestRejectionPersistence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar").id
        ident = cls.env["l10n_latam.identification.type"].search([("l10n_ar_afip_code", "=", "80")], limit=1)
        cls.company.partner_id.write({"vat": "20431432227", "l10n_latam_identification_type_id": ident.id})
        cls.journal = cls.env["account.journal"].search([("type", "=", "sale")], limit=1)
        cls.journal.l10n_ar_afip_pos_system = "RAW_MAW"
        cls.journal.l10n_ar_afip_pos_number = 4
        cls.doc_type = cls.env["l10n_latam.document.type"].search(
            [("code", "=", "11"), ("country_id.code", "=", "AR")], limit=1
        )
        ident = cls.env["l10n_latam.identification.type"].search([("l10n_ar_afip_code", "=", "80")], limit=1)
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "CUIT Partner",
                "vat": "20111111112",
                "l10n_latam_identification_type_id": ident.id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "country_id": cls.env.ref("base.ar").id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test Product", "type": "consu", "list_price": 100, "sale_ok": True}
        )

    def _create_invoice(self):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "invoice_date": "2026-09-01",
                "l10n_latam_document_type_id": self.doc_type.id,
                "invoice_line_ids": [
                    (0, 0, {"product_id": self.product.id, "name": "x", "quantity": 1, "price_unit": 100.0})
                ],
            }
        )

    def test_rejection_writes_diagnostics_and_commits(self):
        invoice = self._create_invoice()
        response = {
            "afip_auth_code": False,
            "afip_result": "R",
            "afip_xml_request": "<request/>",
            "afip_xml_response": "<response/>",
            "observations": False,
            "afip_errors": {"Code": 10016, "Msg": "fecha no corresponde"},
        }
        zero_amounts = {
            "vat_untaxed_base_amount": 0,
            "vat_taxable_amount": 0,
            "vat_exempt_base_amount": 0,
            "not_vat_taxes_amount": 0,
            "vat_amount": 0,
        }

        def fake_call(method, obj, mode="eval", **kwargs):
            if method.name == "last_invoice":
                return 0
            return dict(response)

        with (
            patch.object(type(invoice), "_get_rounded_base_and_tax_lines", return_value=([], [])),
            patch.object(type(invoice), "_l10n_ar_get_amounts", lambda self, base_lines=None: dict(zero_amounts)),
            patch.object(ResCompany, "_get_environment_type", return_value="homologation"),
            patch.object(ResCompany, "get_key_and_certificate", return_value=(None, None)),
            patch.object(ArcaWsMethod, "call_arca_method", fake_call),
            patch.object(self.env.cr, "commit") as commit,
        ):
            invoice.invalidate_recordset(["validation_type"])
            a_invoices, r_invoices = invoice.do_pyafipws_request_cae()

        self.assertEqual(r_invoices, invoice)
        self.assertEqual(a_invoices, self.env["account.move"])
        self.assertEqual(invoice.afip_result, "R")
        self.assertIn("10016", invoice.afip_message)
        self.assertEqual(invoice.afip_xml_request, "<request/>")
        self.assertEqual(invoice.afip_xml_response, "<response/>")
        self.assertTrue(commit.called)
