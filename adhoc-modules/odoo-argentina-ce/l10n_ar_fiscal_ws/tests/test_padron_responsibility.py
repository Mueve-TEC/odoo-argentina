"""Tests for padrón responsibility mapping."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws")
class TestPadronResponsibility(TransactionCase):
    """Responsibility mapping mirrors pyafipws WSSrPadronA5 + l10n_ar:

    - Monotributista (NI + monotributo S) -> RM
    - Responsable Inscripto (AC)           -> IVARI
    - IVA Exento (EX)                      -> IVAE
    - No inscripto sin monotributo (NI)    -> CF
    """

    @classmethod
    def setUpClass(cls):
        """Create a partner used by all responsibility tests."""
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def _vals(self, **kwargs):
        """Build parse_census_vals output for a given responsibility combo."""
        census = {
            "imp_iva": "NI",
            "monotributo": "S",
            "denominacion": "TEST, PERSONA",
            "direccion": "Av Test 123",
            "localidad": "CORDOBA",
            "cod_postal": "5000",
            "provincia_code": "X",
        }
        census.update(kwargs)
        return self.partner.parse_census_vals(census)

    def test_monotributista_rm(self):
        """NI + monotributo S maps to res_RM."""
        vals = self._vals()
        self.assertEqual(vals["l10n_ar_afip_responsibility_type_id"], self.env.ref("l10n_ar.res_RM").id)

    def test_responsable_inscripto_ivari(self):
        """AC maps to res_IVARI."""
        vals = self._vals(imp_iva="AC", monotributo="N")
        self.assertEqual(vals["l10n_ar_afip_responsibility_type_id"], self.env.ref("l10n_ar.res_IVARI").id)

    def test_iva_exento_ivae(self):
        """EX maps to res_IVAE."""
        vals = self._vals(imp_iva="EX", monotributo="N")
        self.assertEqual(vals["l10n_ar_afip_responsibility_type_id"], self.env.ref("l10n_ar.res_IVAE").id)

    def test_no_inscripto_sin_monotributo_cf(self):
        """NI without monotributo maps to res_CF."""
        vals = self._vals(imp_iva="NI", monotributo="N")
        self.assertEqual(vals["l10n_ar_afip_responsibility_type_id"], self.env.ref("l10n_ar.res_CF").id)
