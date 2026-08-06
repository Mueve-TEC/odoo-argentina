from unittest.mock import patch

from odoo.addons.l10n_ar_fiscal_ws.models.arcaws import ArcaWsMethod
from odoo.addons.l10n_ar_fiscal_ws.models.res_partner import ResPartner
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws")
class TestPadronErrors(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "vat": "20306606108",
                "l10n_latam_identification_type_id": cls.env.ref("l10n_ar.it_cuit").id,
            }
        )

    def _arca_response(self, error_key=None, error_msg=None):
        persona = {
            "datosGenerales": {
                "idPersona": 20306606108,
                "apellido": "TEST",
                "nombre": "PARTNER",
                "tipoPersona": "FISICA",
                "domicilioFiscal": {
                    "direccion": "Av Test 123",
                    "localidad": "CORDOBA",
                    "idProvincia": 3,
                },
            }
        }
        if error_key:
            persona[error_key] = {"error": error_msg}
        return {"persona": [persona]}

    def _get_data(self):
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=self._arca_response()):
            return self.partner.get_data_from_padron_arca()

    def test_error_constancia_raises_user_error(self):
        response = self._arca_response("errorConstancia", "pendiente domicilio fiscal electronico")
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=response):
            with self.assertRaises(UserError) as ctx:
                self.partner.get_data_from_padron_arca()
        self.assertIn("pendiente domicilio fiscal electronico", str(ctx.exception))

    def test_error_monotributo_raises_user_error(self):
        response = self._arca_response("errorMonotributo", "error en monotributo")
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=response):
            with self.assertRaises(UserError) as ctx:
                self.partner.get_data_from_padron_arca()
        self.assertIn("error en monotributo", str(ctx.exception))

    def test_error_regimen_general_raises_user_error(self):
        response = self._arca_response("errorRegimenGeneral", "error en regimen general")
        with patch.object(ArcaWsMethod, "call_arca_method", return_value=response):
            with self.assertRaises(UserError) as ctx:
                self.partner.get_data_from_padron_arca()
        self.assertIn("error en regimen general", str(ctx.exception))

    def test_no_error_does_not_raise(self):
        vals = self._get_data()
        self.assertIsInstance(vals, dict)
        self.assertEqual(vals["street"], "Av Test 123")

    def test_wizard_arca_error_is_not_blocking(self):
        """An ARCA per-partner error must not block the wizard (skippable)."""
        wizard = self.env["res.partner.update.from.padron.wizard"].create({"partner_id": self.partner.id})
        with patch.object(
            ResPartner,
            "get_data_from_padron_arca",
            side_effect=UserError(
                "La CUIT registra pendiente la constitucion del domicilio fiscal electronico RG 4280/18"
            ),
        ):
            result = wizard.change_partner()
        self.assertEqual(
            wizard.arca_error_message,
            "La CUIT registra pendiente la constitucion del domicilio fiscal electronico RG 4280/18",
        )
        self.assertIn("warning", result)
