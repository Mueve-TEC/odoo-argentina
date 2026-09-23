"""Tests for ARCA request hardening helpers (PR #104 port, W5b/W6/W7)."""

from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.l10n_ar_fiscal_ws.models.res_company import ResCompany
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws_fe")
class TestAccountMoveArcaHelpers(TransactionCase):
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
        cls.doc_type_nc = cls.env["l10n_latam.document.type"].search(
            [("code", "=", "13"), ("country_id.code", "=", "AR")], limit=1
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

    def _create_invoice(self, move_type="out_invoice", doc_type=None, **kwargs):
        vals = {
            "move_type": move_type,
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_date": "2026-09-01",
            "l10n_latam_document_type_id": (doc_type or self.doc_type).id,
            "invoice_line_ids": [
                (0, 0, {"product_id": self.product.id, "name": "x", "quantity": 1, "price_unit": 100.0})
            ],
        }
        vals.update(kwargs)
        return self.env["account.move"].create(vals)

    def test_safe_document_number_parts_from_document_number(self):
        invoice = self._create_invoice(l10n_latam_document_number="00004-00000001")
        self.assertEqual(
            invoice._l10n_ar_safe_document_number_parts(),
            {"point_of_sale": 4, "invoice_number": 1},
        )

    def test_safe_document_number_parts_from_name(self):
        invoice = self._create_invoice()
        invoice.name = "FA-C 00004-00000007"
        self.assertEqual(
            invoice._l10n_ar_safe_document_number_parts(),
            {"point_of_sale": 4, "invoice_number": 7},
        )

    def test_safe_document_number_parts_returns_false(self):
        invoice = self._create_invoice()
        self.assertFalse(invoice._l10n_ar_safe_document_number_parts())

    def test_get_related_invoices_data_credit_note(self):
        origin = self._create_invoice(
            l10n_latam_document_number="00004-00000001",
            afip_auth_mode="CAE",
            afip_auth_code="86380921654850",
        )
        credit_note = self._create_invoice(
            move_type="out_refund",
            doc_type=self.doc_type_nc,
            reversed_entry_id=origin.id,
        )
        self.assertEqual(credit_note.get_related_invoices_data(), origin)

    def test_get_related_invoices_data_without_number_raises(self):
        origin = self._create_invoice(afip_auth_mode="CAE", afip_auth_code="86380921654850")
        credit_note = self._create_invoice(
            move_type="out_refund",
            doc_type=self.doc_type_nc,
            reversed_entry_id=origin.id,
        )
        with self.assertRaises(UserError):
            credit_note.get_related_invoices_data()

    def test_get_related_invoices_data_non_credit_note_is_empty(self):
        invoice = self._create_invoice()
        self.assertFalse(invoice.get_related_invoices_data())

    def test_get_arca_cuit_uses_confirmed_alias(self):
        self.env["ir.config_parameter"].sudo().set_param("arcaws.env.type", "homologation")
        self.env["arcaws.certificate_alias"].create(
            {
                "company_id": self.company.id,
                "country_id": self.env.ref("base.ar").id,
                "city": "Rosario",
                "department": "IT",
                "common_name": "ARCA WS",
                "company_cuit": "30714295698",
                "type": "homologation",
                "state": "confirmed",
            }
        )
        self.assertEqual(self.company._get_arca_cuit(), "30714295698")

    def test_get_arca_cuit_falls_back_to_partner_vat(self):
        self.env["ir.config_parameter"].sudo().set_param("arcaws.env.type", "homologation")
        self.assertEqual(self.company._get_arca_cuit(), "20431432227")

    def test_request_template_guards(self):
        invoice = self._create_invoice(
            l10n_latam_document_number="00004-00000001",
            l10n_ar_afip_service_start="2026-09-01",
            l10n_ar_afip_service_end="2026-09-30",
        )
        invoice.l10n_ar_payment_foreign_currency = False
        invoice.invoice_currency_rate = 0.0
        method = self.env["arcaws.method"].search(
            [("name", "=", "request_invoice_authorization"), ("arcaws_id.code", "=", "wsfe")]
        )
        captured = {}

        def fake_service(method_name, data):
            captured["data"] = data
            return {}

        connection = SimpleNamespace(sign="s", token="t", call_arca_service=fake_service)
        amounts = {
            "vat_untaxed_base_amount": 0,
            "vat_taxable_amount": 100,
            "vat_exempt_base_amount": 0,
            "not_vat_taxes_amount": 0,
            "vat_amount": 0,
        }
        with patch.object(ResCompany, "arca_get_connection", return_value=connection):
            method.call_arca_method(
                obj=invoice,
                mode="exec",
                extra_values={"next_invoice_number": 1, "amounts": amounts, "arca_document_code": "80"},
            )
        request = captured["data"]["FeCAEReq"]["FeDetReq"]["FECAEDetRequest"]
        self.assertEqual(request["Concepto"], 1)
        self.assertEqual(request["CanMisMonExt"], "N")
        self.assertEqual(request["MonCotiz"], 1.0)
        self.assertEqual(captured["data"]["Auth"]["Cuit"], "20431432227")

    def test_request_template_includes_cbtesasoc_for_credit_note(self):
        origin = self._create_invoice(
            l10n_latam_document_number="00004-00000001",
            afip_auth_mode="CAE",
            afip_auth_code="86380921654850",
        )
        credit_note = self._create_invoice(
            move_type="out_refund",
            doc_type=self.doc_type_nc,
            reversed_entry_id=origin.id,
            l10n_ar_afip_service_start="2026-09-01",
            l10n_ar_afip_service_end="2026-09-30",
        )
        method = self.env["arcaws.method"].search(
            [("name", "=", "request_invoice_authorization"), ("arcaws_id.code", "=", "wsfe")]
        )
        captured = {}

        def fake_service(method_name, data):
            captured["data"] = data
            return {}

        connection = SimpleNamespace(sign="s", token="t", call_arca_service=fake_service)
        amounts = {
            "vat_untaxed_base_amount": 0,
            "vat_taxable_amount": 100,
            "vat_exempt_base_amount": 0,
            "not_vat_taxes_amount": 0,
            "vat_amount": 0,
        }
        with patch.object(ResCompany, "arca_get_connection", return_value=connection):
            method.call_arca_method(
                obj=credit_note,
                mode="exec",
                extra_values={"next_invoice_number": 1, "amounts": amounts, "arca_document_code": "99"},
            )
        asoc = captured["data"]["FeCAEReq"]["FeDetReq"]["FECAEDetRequest"]["CbtesAsoc"]
        self.assertEqual(len(asoc), 1)
        self.assertEqual(
            asoc[0]["CbteAsoc"],
            {
                "Tipo": "11",
                "PtoVta": 4,
                "Nro": 1,
                "Cuit": "20431432227",
                "CbteFch": "20260901",
            },
        )
