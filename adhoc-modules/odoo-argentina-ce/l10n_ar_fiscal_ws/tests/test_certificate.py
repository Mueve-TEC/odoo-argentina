"""Tests for ARCA certificate / certificate-alias handling (PR #104 port)."""

from cryptography import x509
from cryptography.x509.oid import NameOID
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "l10n_ar_fiscal_ws")
class TestCertificate(TransactionCase):
    """W1: malformed certificates must raise a friendly UserError (not a
    TypeError from the error handler). W2: the CSR wizard must work per record
    and store text (not bytes) values."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country_ar = cls.env.ref("base.ar")

    def _create_alias(self, name="ARCA WS Test", **kwargs):
        vals = {
            "company_id": self.company.id,
            "country_id": self.country_ar.id,
            "city": "Rosario",
            "department": "IT",
            "common_name": name,
            "company_cuit": "20431432227",
            "type": "homologation",
            "state": "confirmed",
        }
        vals.update(kwargs)
        return self.env["arcaws.certificate_alias"].create(vals)

    def test_get_certificate_malformed_raises_user_error(self):
        alias = self._create_alias()
        cert = self.env["arcaws.certificate"].create({"alias_id": alias.id, "crt": "not a cert", "csr": "x"})
        with self.assertRaises(UserError) as error:
            cert.get_certificate()
        self.assertIn("Wrong Certificate", str(error.exception))

    def test_generate_key_stores_text(self):
        alias = self._create_alias()
        alias.generate_key()
        self.assertIsInstance(alias.key, str)
        self.assertTrue(alias.key.startswith("-----BEGIN RSA PRIVATE KEY-----"))
        self.assertNotIn("b'", alias.key)

    def test_create_certificate_request_single_alias(self):
        alias = self._create_alias("Alias Single")
        alias.action_create_certificate_request()
        self.assertEqual(len(alias.certificate_ids), 1)
        csr = alias.certificate_ids[:1]
        self.assertIsInstance(csr.csr, str)
        self.assertTrue(csr.csr.startswith("-----BEGIN CERTIFICATE REQUEST-----"))
        parsed = x509.load_pem_x509_csr(csr.csr.encode("ascii"))
        common_names = parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        self.assertEqual(common_names[0].value, "Alias Single")
        serial = parsed.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
        self.assertEqual(serial[0].value, "CUIT 20431432227")

    def test_create_certificate_request_multi_record_keeps_records_apart(self):
        alias_a = self._create_alias("Alias A", company_cuit="20431432227")
        alias_b = self._create_alias("Alias B", company_cuit="30714295698")
        (alias_a | alias_b).action_create_certificate_request()
        for alias, expected_cn, expected_cuit in (
            (alias_a, "Alias A", "CUIT 20431432227"),
            (alias_b, "Alias B", "CUIT 30714295698"),
        ):
            csr = alias.certificate_ids[:1]
            self.assertEqual(csr.alias_id, alias)
            parsed = x509.load_pem_x509_csr(csr.csr.encode("ascii"))
            self.assertEqual(
                parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                expected_cn,
            )
            self.assertEqual(
                parsed.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)[0].value,
                expected_cuit,
            )
