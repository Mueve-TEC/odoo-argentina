"""Helpers to surface ARCA web-service availability problems clearly.

When ARCA (or something in between, e.g. a proxy) is down it answers with an
HTML error page instead of SOAP. pyafipws/pysimplesoap then fail while parsing
that page (``ExpatError: mismatched tag``) and the cashier/accountant sees a
cryptic traceback. These helpers turn those cases into an actionable message.
"""
from odoo import _
from odoo.exceptions import UserError

# Fragments found in the errors raised for non-SOAP/unreachable responses.
_ARCA_UNAVAILABLE_HINTS = (
    'mismatched tag',
    'expat',
    'not well-formed',
    'doctype html',
    'bad gateway',
    'service unavailable',
    'internal server error',
    'http error 5',
    'remote end closed',
    'timed out',
    'temporary failure',
    'name or service not known',
    'connection reset',
)


def is_arca_unavailable_error(error):
    """Return True when *error* looks like ARCA being down/unreachable."""
    text = str(error).lower()
    return any(hint in text for hint in _ARCA_UNAVAILABLE_HINTS)


def raise_arca_unavailable(afip_ws, error):
    """Raise a clear UserError for an unreachable/invalid ARCA service."""
    raise UserError(_(
        'El servicio de ARCA (%(ws)s) no está disponible o devolvió una '
        'respuesta inválida. Reintente en unos minutos; si el problema '
        'persiste verifique la conexión a internet.\n\nDetalle: %(error)s'
    ) % {'ws': afip_ws, 'error': error})
