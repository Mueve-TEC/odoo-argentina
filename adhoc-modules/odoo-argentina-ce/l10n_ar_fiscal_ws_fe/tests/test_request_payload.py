"""Regresiones del payload de FECAESolicitar (plantilla ``data/arcaws.xml``).

Errores reales vistos en homologación que motivaron cada caso:

* ``AttributeError: 'bool' object has no attribute 'strftime'`` — la factura se
  manda a ARCA con concepto 2/3/4 y las fechas de servicio en ``False`` porque
  ``l10n_ar`` las completa recién en ``_post()``, después del pedido de CAE.
* ARCA ``(10035) El campo FchVtoPago es obligatorio si se informa FchServDesde
  y/o FchServHasta`` — la plantilla solo mandaba ``FchVtoPago`` en FCE.
* ``KeyError: 'PeriodoAsoc'`` — el dict nunca se creaba.
* Solo se exportaba la última tasa de IVA: ``AlicIva`` se reiniciaba dentro
  del ``for``.
* Payload FCE sin cuenta bancaria vinculada: solo el opcional de transmisión
  (Id 27), sin ``Id 2101``.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from odoo.addons.l10n_ar_fiscal_ws.models.arcaws import ArcaWsMethod
from odoo.addons.l10n_ar_fiscal_ws.models.res_company import ResCompany
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

AMOUNTS = {
    "vat_untaxed_base_amount": 0,
    "vat_taxable_amount": 100,
    "vat_exempt_base_amount": 0,
    "not_vat_taxes_amount": 0,
    "vat_amount": 21,
}
ZERO_AMOUNTS = {key: 0 for key in AMOUNTS}
REJECTED_RESPONSE = {
    "afip_auth_code": False,
    "afip_result": "R",
    "afip_xml_request": "<request/>",
    "afip_xml_response": "<response/>",
    "observations": False,
    "afip_errors": {"Code": 10016, "Msg": "fecha no corresponde"},
}


@tagged("post_install", "l10n_ar_fiscal_ws_fe")
class TestFeCaeReqPayload(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref("base.ar").id
        ident = cls.env["l10n_latam.identification.type"].search([("l10n_ar_afip_code", "=", "80")], limit=1)
        cls.company.partner_id.write({"vat": "20431432227", "l10n_latam_identification_type_id": ident.id})
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("l10n_latam_use_documents", "=", True)], limit=1
        )
        # Mientras el journal no tenga ``arcaws``, crear facturas no consulta a
        # ARCA (_get_starting_sequence usa la secuencia normal): los tests de
        # payload así no dependen de certificados. El test de wiring lo activa.
        cls.journal.l10n_ar_afip_pos_system = False
        cls.doc_type = cls.env["l10n_latam.document.type"].search(
            [("code", "=", "11"), ("country_id.code", "=", "AR")], limit=1
        )
        cls.doc_type_fce = cls.env["l10n_latam.document.type"].search(
            [("code", "=", "201"), ("country_id.code", "=", "AR")], limit=1
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
        cls.product_consu = cls.env["product.product"].create(
            {"name": "Test Product", "type": "consu", "list_price": 100, "sale_ok": True}
        )
        cls.product_service = cls.env["product.product"].create(
            {"name": "Test Service", "type": "service", "list_price": 50, "sale_ok": True}
        )

    def _create_invoice(self, doc_type=None, **kwargs):
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_date": "2026-09-01",
            "l10n_latam_document_type_id": (doc_type or self.doc_type).id,
            "invoice_line_ids": [
                (0, 0, {"product_id": self.product_consu.id, "name": "x", "quantity": 1, "price_unit": 100.0})
            ],
        }
        vals.update(kwargs)
        return self.env["account.move"].create(vals)

    def _create_mixed_invoice(self, **kwargs):
        """Líneas consu + servicio -> ``l10n_ar_afip_concept`` = '3'."""
        kwargs.setdefault(
            "invoice_line_ids",
            [
                (0, 0, {"product_id": self.product_consu.id, "name": "libro", "quantity": 1, "price_unit": 100.0}),
                (0, 0, {"product_id": self.product_service.id, "name": "envio", "quantity": 1, "price_unit": 50.0}),
            ],
        )
        return self._create_invoice(**kwargs)

    def _build_request(self, invoice, amounts=None, **extra_values):
        """Evalúa la plantilla real y devuelve FECAEDetRequest."""
        method = self.env["arcaws.method"].search(
            [("name", "=", "request_invoice_authorization"), ("arcaws_id.code", "=", "wsfe")]
        )
        captured = {}

        def fake_service(method_name, data):
            captured["data"] = data
            return {}

        connection = SimpleNamespace(sign="s", token="t", call_arca_service=fake_service)
        extra = {
            "next_invoice_number": 1,
            "amounts": dict(amounts or AMOUNTS),
            "arca_document_code": invoice.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code,
            "condicion_iva_receptor": invoice._l10n_ar_get_receptor_vat_condition(),
        }
        extra.update(extra_values)
        with patch.object(ResCompany, "arca_get_connection", return_value=connection):
            method.call_arca_method(obj=invoice, mode="exec", extra_values=extra)
        return captured["data"]["FeCAEReq"]["FeDetReq"]["FECAEDetRequest"]

    def _enable_arca_journal(self):
        self.assertTrue(
            self.env["arcaws"].search([("code", "=", "wsfe")], limit=1),
            "Falta el registro arcaws 'wsfe'",
        )
        self.journal.l10n_ar_afip_pos_system = "RAW_MAW"
        self.journal.l10n_ar_afip_pos_number = 4

    def test_service_dates_filled_before_building_request(self):
        """El CAE se pide con las fechas de servicio ya completas (no False)."""
        invoice = self._create_mixed_invoice()
        self.assertEqual(invoice.l10n_ar_afip_concept, "3")
        self.assertFalse(invoice.l10n_ar_afip_service_start)
        self.assertFalse(invoice.l10n_ar_afip_service_end)
        self._enable_arca_journal()

        captured = {}

        def fake_call(method, obj, mode="eval", **kwargs):
            if method.name == "last_invoice":
                return 0
            captured["service_dates"] = (obj.l10n_ar_afip_service_start, obj.l10n_ar_afip_service_end)
            return dict(REJECTED_RESPONSE)

        with (
            patch.object(type(invoice), "_get_rounded_base_and_tax_lines", return_value=([], [])),
            patch.object(type(invoice), "_l10n_ar_get_amounts", lambda self, base_lines=None: dict(ZERO_AMOUNTS)),
            patch.object(type(self.journal), "_get_last_invoice_number", return_value=0),
            patch.object(ResCompany, "_get_environment_type", return_value="homologation"),
            patch.object(ResCompany, "get_key_and_certificate", return_value=(None, None)),
            patch.object(ArcaWsMethod, "call_arca_method", fake_call),
            patch.object(self.env.cr, "commit"),
        ):
            invoice.invalidate_recordset(["validation_type"])
            accepted, rejected = invoice.do_pyafipws_request_cae()

        self.assertEqual(
            captured["service_dates"],
            (date(2026, 9, 1), date(2026, 9, 30)),
            "FchServDesde/Hasta tenían que estar completas antes de armar el request",
        )
        self.assertEqual(rejected, invoice)
        self.assertFalse(accepted)
        self.assertEqual(invoice.afip_result, "R")

    def test_missing_service_dates_raises_clear_error(self):
        """Sin fechas de servicio se avisa con UserError, no con AttributeError."""
        invoice = self._create_mixed_invoice()
        self._enable_arca_journal()

        with (
            patch.object(type(invoice), "_set_afip_service_dates"),
            patch.object(ResCompany, "_get_environment_type", return_value="homologation"),
            patch.object(ResCompany, "get_key_and_certificate", return_value=(None, None)),
            patch.object(ArcaWsMethod, "call_arca_method") as call_arca,
        ):
            invoice.invalidate_recordset(["validation_type"])
            with self.assertRaises(UserError) as error:
                invoice.do_pyafipws_request_cae()

        self.assertIn("fechas de servicio", str(error.exception))
        call_arca.assert_not_called()

    def test_request_sends_fch_vto_pago_with_service_dates(self):
        """ARCA 10035: FchVtoPago es obligatorio con FchServDesde/Hasta."""
        invoice = self._create_mixed_invoice(
            l10n_ar_afip_service_start="2026-09-01",
            l10n_ar_afip_service_end="2026-09-30",
        )
        self.assertEqual(invoice.l10n_ar_afip_concept, "3")
        request = self._build_request(invoice)

        self.assertEqual(request["FchServDesde"], "20260901")
        self.assertEqual(request["FchServHasta"], "20260930")
        self.assertEqual(
            request["FchVtoPago"],
            (invoice.invoice_date_due or invoice.invoice_date).strftime("%Y%m%d"),
        )
        self.assertEqual(len(request["FchVtoPago"]), 8)

    def test_request_sends_every_iva_rate(self):
        """AlicIva debe traer todas las tasas, no solo la última del loop."""
        tax_codes = ("4", "5")
        taxes = self.env["account.tax"].browse()
        for code in tax_codes:
            tax = self.env["account.tax"].search(
                [("type_tax_use", "=", "sale"), ("tax_group_id.l10n_ar_vat_afip_code", "=", code)], limit=1
            )
            if not tax:
                self.skipTest("Falta un impuesto de venta AR con código AFIP %s" % code)
            taxes |= tax
        invoice = self._create_invoice(
            l10n_ar_afip_service_start="2026-09-01",
            l10n_ar_afip_service_end="2026-09-30",
            invoice_line_ids=[
                (
                    0,
                    0,
                    {
                        "product_id": self.product_consu.id,
                        "name": "a",
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [(6, 0, taxes[0].ids)],
                    },
                ),
                (
                    0,
                    0,
                    {
                        "product_id": self.product_service.id,
                        "name": "b",
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [(6, 0, taxes[1].ids)],
                    },
                ),
            ],
        )
        self.assertEqual(len(invoice._get_vat()), 2)

        request = self._build_request(invoice)
        alic_iva = request["Iva"]["AlicIva"]

        self.assertEqual(len(alic_iva), 2, alic_iva)
        self.assertEqual({line["Id"] for line in alic_iva}, set(tax_codes))

    def test_request_sends_periodo_asoc(self):
        """El bloque PeriodoAsoc debe crear su dict (antes: KeyError)."""
        invoice = self._create_mixed_invoice(
            afip_associated_period_from="2026-08-01",
            afip_associated_period_to="2026-08-31",
            l10n_ar_afip_service_start="2026-09-01",
            l10n_ar_afip_service_end="2026-09-30",
        )
        request = self._build_request(invoice)

        self.assertEqual(
            request["PeriodoAsoc"],
            {"FchDesde": "20260801", "FchHasta": "20260831"},
        )

    def test_request_fce_without_bank_account(self):
        """FCE sin cuenta vinculada: solo el opcional de transmisión."""
        self.company.l10n_ar_afip_fce_transmission = "ADC"
        invoice = self._create_invoice(doc_type=self.doc_type_fce)
        self.assertFalse(invoice.partner_bank_id)

        request = self._build_request(invoice)
        opcionales = request["Opcionales"]["Opcional"]

        self.assertEqual(opcionales, [{"Id": 27, "Valor": "ADC"}])
        self.assertTrue(request["FchVtoPago"])

    def test_request_aborts_before_burning_cae_on_name_collision(self):
        """El desfase entre el contador de ARCA y la base local se detecta
        antes de pedir el CAE (antes revienta el índice único recién al
        postear, con el CAE ya commiteado)."""
        move_model = type(self.env["account.move"])
        journal_model = type(self.journal)
        with (
            patch.object(journal_model, "_get_last_invoice_number", return_value=4),
            patch.object(move_model, "_get_rounded_base_and_tax_lines", return_value=([], [])),
            patch.object(move_model, "_l10n_ar_get_amounts", lambda self, base_lines=None: dict(ZERO_AMOUNTS)),
            patch.object(ResCompany, "_get_environment_type", return_value="homologation"),
            patch.object(ResCompany, "get_key_and_certificate", return_value=(None, None)),
            patch.object(ArcaWsMethod, "call_arca_method") as call_arca,
            patch.object(self.env.cr, "commit"),
        ):
            self._enable_arca_journal()
            invoice = self._create_invoice()
            expected_name = invoice._get_formatted_sequence(5)

            # Otro comprobante ya ocupó ese número en el diario.
            posted = self._create_invoice()
            posted.state = "posted"
            self.assertEqual(posted.name, expected_name)

            invoice.invalidate_recordset(["validation_type"])
            with self.assertRaises(UserError) as error:
                invoice.do_pyafipws_request_cae()

        message = str(error.exception)
        self.assertIn(expected_name, message)
        self.assertIn("Último comprobante autorizado en ARCA: 4", message)
        # No se llegó a ARCA: no hay CAE que quemar.
        call_arca.assert_not_called()
