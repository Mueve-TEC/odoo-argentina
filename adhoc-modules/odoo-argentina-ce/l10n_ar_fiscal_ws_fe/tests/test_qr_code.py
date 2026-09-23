"""Tests for the ARCA QR code payload (PR #104 port, W4)."""

import base64
import json
from urllib.parse import parse_qs, urlparse

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws_fe")
class TestQrCode(TransactionCase):
    """Anonymous final consumers must encode tipoDocRec 99 / nroDocRec 0, and
    ctz must be the reciprocal of the invoice currency rate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar").id
        cls.journal = cls.env["account.journal"].search([("type", "=", "sale")], limit=1)
        cls.journal.l10n_ar_afip_pos_system = "RAW_MAW"
        cls.journal.l10n_ar_afip_pos_number = 4
        cls.doc_type_c = cls.env["l10n_latam.document.type"].search(
            [("code", "=", "11"), ("country_id.code", "=", "AR")], limit=1
        )
        cls.ident_cuit = cls.env["l10n_latam.identification.type"].search([("l10n_ar_afip_code", "=", "80")], limit=1)
        cls.ident_sigd = cls.env["l10n_latam.identification.type"].search([("l10n_ar_afip_code", "=", "99")], limit=1)
        cls.company.partner_id.write({"vat": "20431432227", "l10n_latam_identification_type_id": cls.ident_cuit.id})
        cls.partner_cuit = cls.env["res.partner"].create(
            {
                "name": "CUIT Partner",
                "vat": "20111111112",
                "l10n_latam_identification_type_id": cls.ident_cuit.id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_IVARI").id,
                "country_id": cls.env.ref("base.ar").id,
            }
        )
        cls.partner_cf = cls.env["res.partner"].create(
            {
                "name": "Consumidor Final Anonimo",
                "l10n_latam_identification_type_id": cls.ident_sigd.id,
                "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_CF").id,
                "country_id": cls.env.ref("base.ar").id,
            }
        )

    def _create_invoice(self, partner, **kwargs):
        vals = {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": self.journal.id,
            "invoice_date": "2026-09-01",
            "l10n_latam_document_type_id": self.doc_type_c.id,
            "l10n_latam_document_number": "00004-00000001",
            "invoice_line_ids": [(0, 0, {"name": "x", "quantity": 1, "price_unit": 100.0})],
        }
        vals.update(kwargs)
        return self.env["account.move"].create(vals)

    def _decode_qr(self, move):
        query = parse_qs(urlparse(move.afip_qr_code).query)
        return json.loads(base64.b64decode(query["p"][0]))

    def test_qr_anonymous_final_consumer(self):
        invoice = self._create_invoice(self.partner_cf)
        invoice.write({"afip_auth_mode": "CAE", "afip_auth_code": "86380921654850"})
        payload = self._decode_qr(invoice)
        self.assertEqual(payload["tipoDocRec"], 99)
        self.assertEqual(payload["nroDocRec"], 0)
        self.assertEqual(payload["tipoCmp"], 11)
        self.assertEqual(payload["ptoVta"], 4)
        self.assertEqual(payload["nroCmp"], 1)

    def test_qr_identified_partner(self):
        invoice = self._create_invoice(self.partner_cuit)
        invoice.write({"afip_auth_mode": "CAE", "afip_auth_code": "86380921654850"})
        payload = self._decode_qr(invoice)
        self.assertEqual(payload["tipoDocRec"], 80)
        self.assertEqual(payload["nroDocRec"], 20111111112)

    def test_qr_ctz_is_reciprocal_of_rate(self):
        invoice = self._create_invoice(self.partner_cuit)
        invoice.write({"afip_auth_mode": "CAE", "afip_auth_code": "86380921654850"})
        self.assertEqual(self._decode_qr(invoice)["ctz"], 1.0)
        invoice.invoice_currency_rate = 0.001
        self.assertEqual(self._decode_qr(invoice)["ctz"], 1000.0)

    def test_qr_not_computed_without_auth_code(self):
        invoice = self._create_invoice(self.partner_cf)
        self.assertFalse(invoice.afip_qr_code)

    def test_qr_not_computed_without_document_number(self):
        invoice = self._create_invoice(self.partner_cf, l10n_latam_document_number=False)
        invoice.write({"afip_auth_mode": "CAE", "afip_auth_code": "86380921654850"})
        self.assertFalse(invoice.afip_qr_code)
