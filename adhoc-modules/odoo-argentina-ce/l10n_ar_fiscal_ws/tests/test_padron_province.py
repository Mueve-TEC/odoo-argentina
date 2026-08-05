"""Tests for padrón province matching via ARCA idProvincia."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws")
class TestPadronProvince(TransactionCase):
    """Province matching uses ARCA idProvincia -> ISO 3166-2:AR code, which is
    accent-proof (descripcionProvincia comes uppercase without accents)."""

    @classmethod
    def setUpClass(cls):
        """Create a partner used by all province tests."""
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def _vals(self, provincia_code, descripcion_provincia=""):
        """Build parse_census_vals output for a given province code."""
        return self.partner.parse_census_vals(
            {
                "imp_iva": "NI",
                "monotributo": "N",
                "denominacion": "TEST",
                "direccion": "Av Test 123",
                "provincia_code": provincia_code,
                "provincia": descripcion_provincia,
            }
        )

    def test_cordoba_code_matches_state(self):
        """idProvincia=3 (code X) must match res.country.state 'X' for AR."""
        state = self.env["res.country.state"].search([("code", "=", "X"), ("country_id.code", "=", "AR")], limit=1)
        self.assertTrue(state)
        vals = self._vals("X", "CORDOBA")
        self.assertEqual(vals["state_id"], state.id)

    def test_caba_code_matches_state(self):
        """idProvincia=0 (code C) must match CABA state."""
        state = self.env["res.country.state"].search([("code", "=", "C"), ("country_id.code", "=", "AR")], limit=1)
        self.assertTrue(state)
        vals = self._vals("C", "CAPITAL FEDERAL")
        self.assertEqual(vals["state_id"], state.id)

    def test_unknown_code_does_not_set_state(self):
        """An unmapped code must not leave a state_id in the vals."""
        vals = self._vals("ZZ", "PROVINCIA INVENTADA")
        self.assertNotIn("state_id", vals)
