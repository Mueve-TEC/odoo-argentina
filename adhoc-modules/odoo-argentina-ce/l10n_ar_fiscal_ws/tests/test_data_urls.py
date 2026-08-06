"""Tests for the wsfecred / padrón service URLs."""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws")
class TestArcaWsDataUrls(TransactionCase):
    """Regression: wsfecred URLs were corrected on commit 34d21b274 (production
    -> serviciosjava, homologation -> fwshomo)."""

    def test_wsfecred_urls_production_are_not_homologation(self):
        """Homologation must never point to production hosts."""
        ws = self.env["arcaws"].search([("code", "=", "wsfecred")], limit=1)
        self.assertTrue(ws)
        self.assertIn("serviciosjava.afip.gob.ar", ws.production_url)
        self.assertIn("fwshomo.afip.gov.ar", ws.homologation_url)
        self.assertNotEqual(ws.production_url, ws.homologation_url)

    def test_padron_service_urls(self):
        """The A5 padrón service keeps its production/homologation hosts."""
        ws = self.env["arcaws"].search([("code", "=", "ws_sr_constancia_inscripcion")], limit=1)
        self.assertTrue(ws)
        self.assertIn("aws.afip.gov.ar", ws.production_url)
        self.assertIn("awshomo.afip.gov.ar", ws.homologation_url)
