##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _arca_ascii(value):
    return (value or "").encode("ascii", "ignore").decode("ascii")


class ArcawsCertificateAlias(models.Model):
    _name = "arcaws.certificate_alias"
    _description = "ARCA Distingish Name / Alias"
    _rec_name = "common_name"

    """
    Para poder acceder a un servicio, la aplicación a programar debe utilizar
    un certificado de seguridad, que se obtiene en la web de arca. Entre otras
    cosas, el certificado contiene un Distinguished Name (DN) que incluye una
    CUIT. Cada DN será identificado por un "alias" o "nombre simbólico",
    que actúa como una abreviación.
    EJ alias: ARCA WS Prod - ADHOC SA
    EJ DN: C=ar, ST=santa fe, L=rosario, O=adhoc s.a., OU=it,
           SERIALNUMBER=CUIT 30714295698, CN=arca web services - adhoc s.a.
    """

    common_name = fields.Char(
        size=64,
        default="ARCA WS",
        help="Just a name, you can leave it this way",
        readonly=True,
        required=True,
    )
    key = fields.Text(
        "Private Key",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        bypass_search_access=True,
        index=True,
    )
    country_id = fields.Many2one(
        "res.country",
        "Country",
        readonly=True,
        required=True,
        ondelete="restrict",
    )
    state_id = fields.Many2one(
        "res.country.state",
        "State",
        readonly=True,
        ondelete="set null",
    )
    city = fields.Char(
        readonly=True,
        required=True,
    )
    department = fields.Char(
        default="IT",
        readonly=True,
        required=True,
    )
    cuit = fields.Char(
        "CUIT",
        compute="_compute_cuit",
        required=True,
    )
    company_cuit = fields.Char(
        "Company CUIT",
        size=16,
        readonly=True,
    )
    service_provider_cuit = fields.Char(
        "Service Provider CUIT",
        size=16,
        readonly=True,
    )
    certificate_ids = fields.One2many(
        "arcaws.certificate",
        "alias_id",
        "Certificates",
        bypass_search_access=True,
    )
    service_type = fields.Selection(
        [("in_house", "In House"), ("outsourced", "Outsourced")],
        default="in_house",
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancel", "Cancelled"),
        ],
        "Status",
        index=True,
        readonly=True,
        default="draft",
        help="* The 'Draft' state is used when a user is creating a new pair "
        "key. Warning: everybody can see the key."
        "\n* The 'Confirmed' state is used when the key is completed with "
        "public or private key."
        "\n* The 'Canceled' state is used when the key is not more used. "
        "You cant use this key again.",
    )
    type = fields.Selection(
        [("production", "Production"), ("homologation", "Homologation")],
        required=True,
        default="production",
        readonly=True,
    )

    @api.onchange("company_id")
    def change_company_name(self):
        if self.company_id:
            common_name = "ARCA WS %s - %s" % (self.type, self.company_id.name)
            self.common_name = common_name[:50]

    @api.depends("company_cuit", "service_provider_cuit", "service_type")
    def _compute_cuit(self):
        for rec in self:
            if rec.service_type == "outsourced":
                rec.cuit = rec.service_provider_cuit
            else:
                rec.cuit = rec.company_cuit

    @api.onchange("company_id")
    def change_company_id(self):
        if self.company_id:
            self.country_id = self.company_id.country_id.id
            self.state_id = self.company_id.state_id.id
            self.city = self.company_id.city
            self.company_cuit = self.company_id.vat

    def action_confirm(self):
        if not self.key:
            self.generate_key()
        self.write({"state": "confirmed"})
        return True

    def generate_key(self, key_length=2048):
        """ """
        # TODO reemplazar todo esto por las funciones nativas de pyarcaws
        for rec in self:
            key = rsa.generate_private_key(public_exponent=65537, key_size=key_length)
            pem = key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
            rec.key = pem.decode("ascii")

    def action_to_draft(self):
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        self.certificate_ids.write({"state": "cancel"})
        return True

    def action_create_certificate_request(self):
        """
        TODO agregar descripcion y ver si usamos pyarcasw para generar esto
        """
        for record in self:
            if not record.key:
                record.generate_key()
            key = serialization.load_pem_private_key(record.key.encode("utf-8"), password=None)
            attributes = [
                x509.NameAttribute(NameOID.COUNTRY_NAME, _arca_ascii(record.country_id.code)),
                x509.NameAttribute(NameOID.LOCALITY_NAME, _arca_ascii(record.city)),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, _arca_ascii(record.company_id.name)),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, _arca_ascii(record.department)),
                x509.NameAttribute(NameOID.COMMON_NAME, _arca_ascii(record.common_name)),
                x509.NameAttribute(NameOID.SERIAL_NUMBER, "CUIT %s" % (record.cuit or "")),
            ]
            if record.state_id:
                attributes.insert(
                    1,
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, _arca_ascii(record.state_id.name)),
                )
            csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name(attributes)).sign(key, hashes.SHA256())
            vals = {
                "csr": csr.public_bytes(serialization.Encoding.PEM).decode("ascii"),
                "alias_id": record.id,
            }
            record.certificate_ids.create(vals)
        return True

    @api.constrains("common_name")
    def check_common_name_len(self):
        if self.filtered(lambda x: x.common_name and len(x.common_name) > 50):
            raise ValidationError(_("The Common Name must be lower than 50 characters long"))
