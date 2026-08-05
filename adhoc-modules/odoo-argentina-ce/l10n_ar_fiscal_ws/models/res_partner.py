##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from zeep.helpers import serialize_object

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    mipyme_required = fields.Boolean(
        string="Must credit invoice",
    )
    mipyme_from_amount = fields.Float(
        string="Credit invoice from amount",
    )
    last_update_census = fields.Date(string="Last update census")

    # Constantes para servicios ARCA - Pueden ser heredadas en módulos custom
    _PADRON_SERVICE_CODE = "ws_sr_constancia_inscripcion"
    _PADRON_METHOD_NAME = "get_persona_list"
    _PADRON_BATCH_SIZE = 100  # Límite de ARCA para consultas masivas
    _PADRON_MAX_ERRORS_TO_SHOW = 10  # Mostrar primeros N errores en UI

    # Mapeo ARCA idProvincia (int) -> código ISO 3166-2:AR de res.country.state
    # Los códigos de Odoo son letras solas (A, B, C...), coincide con la
    # subdivisiones oficiales AR-A, AR-B, AR-C, etc.Usado para matching exacto
    # sin depender de acentos/casing de 'descripcionProvincia' de ARCA
    # (que viene en mayúsculas y sin acentos: 'CORDOBA', 'TUCUMAN'...).
    _ARCA_PROVINCIA_ID_TO_CODE = {
        0: "C",  # Ciudad Autónoma de Buenos Aires
        1: "B",  # Buenos Aires
        2: "K",  # Catamarca
        3: "X",  # Córdoba
        4: "W",  # Corrientes
        5: "E",  # Entre Ríos
        6: "Y",  # Jujuy
        7: "M",  # Mendoza
        8: "F",  # La Rioja
        9: "A",  # Salta
        10: "J",  # San Juan
        11: "D",  # San Luis
        12: "S",  # Santa Fe
        13: "G",  # Santiago del Estero
        14: "T",  # Tucumán
        16: "H",  # Chaco
        17: "U",  # Chubut
        18: "P",  # Formosa
        19: "N",  # Misiones
        20: "Q",  # Neuquén
        21: "L",  # La Pampa
        22: "R",  # Río Negro
        23: "Z",  # Santa Cruz
        24: "V",  # Tierra del Fuego
    }

    # Separo esto para poder heredar de otros
    # modulos y extender los datos
    def parse_census_vals(self, census):
        """Parse census data from ARCA Padrón A5.

        Args:
            census: Dictionary with ARCA response data. Expected keys:
                - denominacion: Company/person name
                - direccion: Fiscal address
                - localidad: City
                - cod_postal: ZIP code
                - provincia: Province name
                - imp_iva: VAT status (S=Active, N=Not inscribed)
                - impuestos: List of tax IDs [10, 11, 12, etc]
                - monotributo: Monotributo status (S/N)
        """

        # Soportar tanto diccionarios como objetos con atributos
        def get_value(data, key, default=""):
            if isinstance(data, dict):
                return data.get(key, default)
            return getattr(data, key, default)

        # porque imp_iva activo puede ser S o AC
        imp_iva = get_value(census, "imp_iva", "N")
        if imp_iva == "S":
            imp_iva = "AC"
        elif imp_iva == "N":
            # por ej. monotributista devuelve N
            imp_iva = "NI"

        vals = {
            "street": get_value(census, "direccion"),
            "city": get_value(census, "localidad"),
            "zip": get_value(census, "cod_postal"),
            "last_update_census": fields.Date.today(),
        }

        # Solo incluir 'name' si denominacion tiene un valor válido
        denominacion = get_value(census, "denominacion")
        if denominacion:
            vals["name"] = denominacion

        # Establecer país Argentina
        country_ar = self.env.ref("base.ar", raise_if_not_found=False)
        if country_ar:
            vals["country_id"] = country_ar.id

        # padron.idProvincia
        monotributo = get_value(census, "monotributo", "N")
        provincia = get_value(census, "provincia")
        provincia_code = get_value(census, "provincia_code", "")

        # CABA puede tener diferentes códigos según la base de datos
        caba_codes = ["C", "CABA", "ABA"]

        # Preferimos matching por código ISO 3166-2:AR (determinista, sin
        # problemas de acentos). Solo caemos a text-search si ARCA no envió
        # idProvincia (caso raro/legacy).
        state = False
        if provincia_code:
            state = self.env["res.country.state"].search(
                [
                    ("code", "=", provincia_code),
                    ("country_id.code", "=", "AR"),
                ],
                limit=1,
            )
            if not state:
                _logger.warning(
                    "Provincia ARCA idProvincia=%s (code=%s) no encontrada en "
                    "res.country.state para AR. Probablemente la base no tiene "
                    "cargada la provincia con ese código.",
                    get_value(census, "id_provincia", provincia_code),
                    provincia_code,
                )
        elif provincia:
            provincia_upper = provincia.upper()
            caba_names = ["CAPITAL", "CIUDAD AUTONOMA", "CABA", "C.A.B.A"]
            is_caba = any(caba_name in provincia_upper for caba_name in caba_names)
            if is_caba:
                state = self.env["res.country.state"].search(
                    [
                        ("code", "in", caba_codes),
                        ("country_id.code", "=", "AR"),
                    ],
                    limit=1,
                )
            else:
                # Fallback: text search (puede fallar con acentos)
                state = self.env["res.country.state"].search(
                    [
                        ("name", "ilike", provincia),
                        ("code", "not in", caba_codes),
                        ("country_id.code", "=", "AR"),
                    ],
                    limit=1,
                )
                if not state:
                    _logger.warning(
                        "No se encontró provincia '%s' (text-search). "
                        "ARCA debería enviar idProvincia para matching exacto.",
                        provincia,
                    )
        if state:
            vals["state_id"] = state.id

        # Intentar determinar tipo de responsabilidad ARCA basado
        # en IVA y monotributo. Solo si el campo existe en el modelo
        # (puede estar en l10n_ar u otro módulo).
        # Nota: "N" se normaliza a "NI" arriba, por lo que aquí
        # imp_iva solo puede ser "AC", "EX" o "NI".
        partner_fields = self.env["res.partner"]._fields
        if partner_fields.get("l10n_ar_afip_responsibility_type_id"):
            try:
                if imp_iva == "NI" and monotributo == "S":
                    # Monotributista
                    vals["l10n_ar_afip_responsibility_type_id"] = self.env.ref("l10n_ar.res_RM").id
                elif imp_iva == "AC":
                    # Responsable Inscripto IVA
                    vals["l10n_ar_afip_responsibility_type_id"] = self.env.ref("l10n_ar.res_IVARI").id
                elif imp_iva == "EX":
                    # IVA Exento
                    vals["l10n_ar_afip_responsibility_type_id"] = self.env.ref("l10n_ar.res_IVAE").id
                elif imp_iva == "NI":
                    # No inscripto y no monotributista → Consumidor Final
                    vals["l10n_ar_afip_responsibility_type_id"] = self.env.ref("l10n_ar.res_CF").id
            except (ValueError, UserError, KeyError, AttributeError) as e:
                _logger.warning("No se pudo establecer tipo de responsabilidad ARCA: %s", e)
            except Exception:
                _logger.exception("Unexpected error al establecer tipo de responsabilidad ARCA")
                raise

        return vals

    def _build_denominacion(self, datos_generales):
        """Construye la denominación desde datos ARCA.

        Args:
            datos_generales: Dict con nombre, apellido, razonSocial

        Returns:
            str o None: Denominación construida o None si no hay datos válidos
        """
        if not isinstance(datos_generales, dict):
            return None

        nombre = (datos_generales.get("nombre") or "").strip()
        apellido = (datos_generales.get("apellido") or "").strip()
        razon_social = (datos_generales.get("razonSocial") or "").strip()

        # Personas jurídicas: solo razonSocial
        if razon_social:
            return razon_social

        # Personas físicas: apellido, nombre
        if apellido:
            return f"{apellido}, {nombre}" if nombre else apellido

        # Solo nombre sin apellido
        if nombre:
            return nombre

        # Sin datos válidos
        return None

    def _transform_arca_persona_to_census(self, persona_data):
        """Transform ARCA persona structure to census format.

        Prepares data for parse_census_vals method.

        Args:
            persona_data: Dictionary with nested ARCA response structure.

        Returns:
            Dictionary with flat structure expected by parse_census_vals.
        """
        # Validación defensiva: verificar que persona_data no sea None
        if not persona_data or not isinstance(persona_data, dict):
            msg = "ARCA no devolvió datos válidos " "(persona_data es None o inválido)"
            raise UserError(_(msg))

        # Construir denominación desde nombre y apellido
        datos_generales = persona_data.get("datosGenerales") or {}
        if not isinstance(datos_generales, dict):
            msg = "ARCA devolvió datos generales inválidos"
            raise UserError(_(msg))

        # Usar método auxiliar para construir denominación
        denominacion = self._build_denominacion(datos_generales)

        if not denominacion:
            # Log para diagnóstico
            cuit = datos_generales.get("idPersona", "desconocido")
            _logger.warning(
                "ARCA no devolvió nombre válido para CUIT %s. "
                "Se omitirá actualizar el campo 'name'. datos_generales: %s",
                cuit,
                datos_generales,
            )

        # Transformar estructura anidada a formato plano
        # con validaciones defensivas
        domicilio = datos_generales.get("domicilioFiscal") or {}
        if not isinstance(domicilio, dict):
            domicilio = {}

        datos_monotributo = persona_data.get("datosMonotributo") or {}
        if not isinstance(datos_monotributo, dict):
            datos_monotributo = {}

        datos_regimen = persona_data.get("datosRegimenGeneral") or {}
        if not isinstance(datos_regimen, dict):
            datos_regimen = {}

        # Extraer impuestos como pyafipws.WSSrPadronA5: unión de
        # datosMonotributo.impuesto + datosRegimenGeneral.impuesto.
        # zeep serializa arrays de un solo elemento como un dict, no como lista.
        def _as_list(v):
            if isinstance(v, dict):
                return [v]
            if isinstance(v, list):
                return v
            return []

        impuestos_raw = _as_list(datos_monotributo.get("impuesto", [])) + _as_list(datos_regimen.get("impuesto", []))
        impuestos_ids = [imp["idImpuesto"] for imp in impuestos_raw if isinstance(imp, dict) and "idImpuesto" in imp]

        # Mapeo idImpuesto → imp_iva (espejo de pyafipws.analizar_datos)
        if 32 in impuestos_ids:
            imp_iva = "EX"
        elif 33 in impuestos_ids:
            imp_iva = "NI"
        elif 34 in impuestos_ids:
            imp_iva = "NA"
        elif 30 in impuestos_ids:
            imp_iva = "S"
        else:
            imp_iva = "N"

        # Monotributo (A5): categoriaMonotributo no vacío → "S" (igual que pyafipws)
        cat_mt = datos_monotributo.get("categoriaMonotributo") or {}
        monotributo = "S" if cat_mt else "N"

        # Mapear idProvincia (int ARCA) a código ISO 3166-2:AR de Odoo
        id_provincia = domicilio.get("idProvincia")
        provincia_code = self._ARCA_PROVINCIA_ID_TO_CODE.get(id_provincia, "")

        result = {
            "direccion": domicilio.get("direccion", ""),
            "localidad": domicilio.get("localidad", ""),
            "cod_postal": domicilio.get("codPostal", ""),
            "provincia": domicilio.get("descripcionProvincia", ""),
            "provincia_code": provincia_code,
            "monotributo": monotributo,
            "imp_iva": imp_iva,
            "tipoPersona": datos_generales.get("tipoPersona", ""),
        }

        # Solo incluir denominacion si tiene un valor válido
        if denominacion:
            result["denominacion"] = denominacion

        return result

    def _get_padron_service_and_method(self, service_code=None, method_name=None):
        """Obtiene el servicio y método ARCAWS para consultas.

        Args:
            service_code: Código del servicio (default: _PADRON_SERVICE_CODE)
            method_name: Nombre del método (default: _PADRON_METHOD_NAME)

        Returns:
            tuple: (arcaws, method_id)

        Raises:
            UserError: Si no se encuentra el servicio o método configurado
        """
        code = service_code or self._PADRON_SERVICE_CODE
        method = method_name or self._PADRON_METHOD_NAME

        arcaws = self.env["arcaws"].search([("code", "=", code)], limit=1)
        if not arcaws:
            msg = _("No se encontró configuración del servicio de padrón")
            raise UserError(msg)

        method_id = arcaws.method_ids.filtered(lambda m: m.name == method)
        if not method_id:
            msg = _("No se encontró el método %s configurado") % method
            raise UserError(msg)

        method_id.ensure_one()
        return arcaws, method_id

    def _validate_and_serialize_arca_response(self, res, context_info="", single=False):
        """Valida y serializa respuesta de servicio ARCA.

        Args:
            res: Respuesta del servicio ARCA (puede ser objeto Zeep o dict)
            context_info: Información de contexto para mensajes de error
            single: Si True, retorna directamente el primer elemento

        Returns:
            list o dict: Lista de personas o persona única si single=True

        Raises:
            UserError: Si la respuesta es inválida o no contiene datos
        """
        if res is None:
            msg = _("ARCA devolvió respuesta vacía para %s")
            raise UserError(msg % context_info)

        # Serializar respuesta Zeep a diccionario Python si es necesario
        if not isinstance(res, dict):
            res = serialize_object(res)

        if not res or not isinstance(res, dict):
            msg = _("Error al serializar respuesta ARCA para %s")
            raise UserError(msg % context_info)

        # Extraer lista de personas
        personas = res.get("persona", [])
        if not personas:
            raise UserError(_("ARCA no devolvió datos para %s") % context_info)

        # Retornar primer elemento si se espera uno solo
        if single:
            if len(personas) > 1:
                _logger.warning(
                    "ARCA devolvió %d personas para %s, esperando 1. Se usará la primera.",
                    len(personas),
                    context_info,
                )
            first_persona = personas[0]
            # Validación adicional para homologación
            if first_persona is None:
                _logger.error(
                    "ARCA devolvió persona None en posición 0 para %s. Respuesta completa: %s",
                    context_info,
                    personas,
                )
            return first_persona

        return personas

    def _transform_and_parse_persona_data(self, persona_data):
        """Transforma datos de persona ARCA a valores de partner Odoo sin alterar el casing.

        Args:
            persona_data: Diccionario con datos de persona desde ARCA

        Returns:
            dict: Valores para actualizar partner

        Raises:
            UserError: Si hay error en la transformación o parseo
        """
        census_data = self._transform_arca_persona_to_census(persona_data)
        vals = self.parse_census_vals(census_data)
        return vals

    def _get_padron_homologation_warning(self):
        """Return a warning message when the padrón service would run against homologation certs.

        The ARCA padrón web service is not reliable in the homologation
        environment: it returns incomplete data, wrong responsibility states
        (e.g. 'Consumidor Final') or empty fields. When no warning applies,
        returns False.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        if company._get_environment_type() == "homologation":
            return _(
                "Estás por usar el servicio de Padrón ARCA con certificados de "
                "homologación.\n\nEl padrón de ARCA no es confiable en "
                "homologación: puede devolver datos incompletos, "
                "responsabilidades erróneas (por ejemplo 'Consumidor Final') o "
                "campos vacíos. Se recomienda usar el entorno de producción con "
                "certificados reales."
            )
        return False

    def update_from_padron_arca(self):
        """Actualiza el partner desde el Padrón ARCA sin wizard."""
        self.ensure_one()
        warning = self._get_padron_homologation_warning()
        if warning:
            raise UserError(warning)
        try:
            partner_vals = self.get_data_from_padron_arca()
            self.write(partner_vals)

            # Mostrar notificación de éxito y refrescar la vista
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Actualización exitosa"),
                    "message": _("Datos actualizados desde el Padrón ARCA"),
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": "res.partner",
                        "res_id": self.id,
                        "view_mode": "form",
                        "views": [[False, "form"]],
                        "target": "current",
                    },
                },
            }
        except UserError:
            raise
        except Exception as e:
            error_msg = _("Error al actualizar desde el Padrón ARCA:\n%s")
            raise UserError(error_msg % str(e))

    def action_update_from_padron_mass(self):
        """Actualiza múltiples partners desde Padrón ARCA.

        Permite actualizar varios contactos en una sola llamada.
        Filtra partners con CUIT válido, agrupa en lotes y consulta
        el Padrón A5 de manera masiva.
        """
        warning = self[:1]._get_padron_homologation_warning()
        if warning:
            raise UserError(warning)

        # Filtrar partners con CUIT válido (tipo 80)
        partners_with_cuit = self.filtered(
            lambda p: p.vat
            and p.l10n_latam_identification_type_id
            and p.l10n_latam_identification_type_id.l10n_ar_afip_code == "80"
        )

        if not partners_with_cuit:
            msg = "No se encontraron contactos con CUIT válido"
            raise UserError(_(msg))

        # Obtener servicio y método usando método auxiliar
        arcaws, method_id = self._get_padron_service_and_method()

        # Procesar en lotes (límite de ARCA)
        batch_size = self._PADRON_BATCH_SIZE
        updated_count = 0
        error_details = []

        # Dividir en lotes
        for i in range(0, len(partners_with_cuit), batch_size):
            batch_partners = partners_with_cuit[i : i + batch_size]
            cuit_list = [p.ensure_vat() for p in batch_partners]

            try:
                # Llamar al servicio ARCA con la lista de CUITs
                res = method_id.call_arca_method(
                    obj=batch_partners[0],
                    extra_values={"cuit_list": cuit_list},
                )

                # Validar y serializar respuesta usando método auxiliar
                try:
                    lote_num = i // batch_size + 1
                    personas = self._validate_and_serialize_arca_response(res, f"lote {lote_num}")
                except UserError as ue:
                    error_details.append(str(ue))
                    _logger.error("Error validando respuesta ARCA: %s", ue)
                    continue

                # Crear diccionario CUIT -> datos
                # (filtrar elementos None o inválidos)
                persona_by_cuit = {}
                for p in personas:
                    if not p or not isinstance(p, dict):
                        continue
                    datos_generales = p.get("datosGenerales")
                    if not datos_generales or not isinstance(datos_generales, dict):
                        _logger.warning(
                            "ARCA devolvió persona sin datosGenerales válidos en lote %s: %s",
                            lote_num,
                            p,
                        )
                        continue
                    id_persona = datos_generales.get("idPersona")
                    if id_persona:
                        persona_by_cuit[str(id_persona)] = p

                # Actualizar cada partner del lote
                for partner in batch_partners:
                    partner_cuit = None
                    try:
                        partner_cuit = partner.ensure_vat()
                        persona_data = persona_by_cuit.get(partner_cuit)

                        if not persona_data:
                            msg = "CUIT %s: Sin datos en respuesta ARCA"
                            error_details.append(_(msg) % partner_cuit)
                            continue

                        # Transformar y parsear usando método auxiliar
                        vals = partner._transform_and_parse_persona_data(persona_data)
                        # Actualizar sin tracking para evitar diálogos confusos
                        partner.with_context(tracking_disable=True).write(vals)
                        updated_count += 1

                    except Exception as e:
                        msg = "CUIT %s: %s"
                        error_details.append(_(msg) % (partner_cuit, str(e)))
                        _logger.warning("Error actualizando partner %s: %s", partner.id, e)

            except Exception as e:
                # Error en todo el lote
                error_details.append(_("Error procesando lote: %s") % str(e))
                _logger.error("Error en lote de actualización masiva: %s", e)

        # Preparar mensaje de resultado
        error_count = len(error_details)

        if updated_count > 0 and error_count == 0:
            title = _("✓ Actualización exitosa")
            message = _("Se actualizaron %d contactos desde el Padrón ARCA") % updated_count
            msg_type = "success"
            sticky = False
        elif updated_count > 0 and error_count > 0:
            title = _("⚠ Actualización parcial")
            message = _("Se actualizaron %d contactos correctamente.\nSe encontraron %d errores:\n\n%s") % (
                updated_count,
                error_count,
                "\n".join(error_details[: self._PADRON_MAX_ERRORS_TO_SHOW]),
            )
            if len(error_details) > self._PADRON_MAX_ERRORS_TO_SHOW:
                message += _("\n... y %d errores más") % (len(error_details) - self._PADRON_MAX_ERRORS_TO_SHOW)
            msg_type = "warning"
            sticky = True
        else:
            title = _("✗ Error en la actualización")
            message = _("No se pudo actualizar ningún contacto.\nErrores encontrados:\n\n%s") % "\n".join(
                error_details[: self._PADRON_MAX_ERRORS_TO_SHOW]
            )
            if len(error_details) > self._PADRON_MAX_ERRORS_TO_SHOW:
                message += _("\n... y %d errores más") % (len(error_details) - self._PADRON_MAX_ERRORS_TO_SHOW)
            msg_type = "danger"
            sticky = True

        # Recargar vista y mostrar notificación
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": msg_type,
                "sticky": sticky,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "res.partner",
                    "name": _("Contactos"),
                    "view_mode": "list,form",
                    "views": [[False, "list"], [False, "form"]],
                    "target": "current",
                    "domain": [],
                    "context": {},
                },
            },
        }

    def get_data_from_padron_arca(self):
        """Get partner data from ARCA Padrón A5.

        Uses get_persona_list method with single CUIT for consistency.

        Returns:
            dict: Partner values to update

        Raises:
            UserError: If data cannot be retrieved or parsed
        """
        self.ensure_one()
        cuit = self.ensure_vat()

        # Obtener servicio y método usando método auxiliar
        arcaws, method_id = self._get_padron_service_and_method()

        error_msg = _(
            "No pudimos actualizar desde padrón ARCA al partner %s (%s).\n"
            "Recomendamos verificar manualmente en la página de ARCA.\n"
            "Obtuvimos este error: %s"
        )

        try:
            # Llamar con lista de un solo CUIT
            res = method_id.call_arca_method(obj=self, extra_values={"cuit_list": [cuit]})

            # Validar y serializar respuesta (single=True retorna directamente)
            persona_data = self._validate_and_serialize_arca_response(res, cuit, single=True)

            # Validación adicional: ARCA en homologación puede devolver estructura vacía
            if not persona_data or not isinstance(persona_data, dict):
                _logger.error(
                    "ARCA devolvió persona_data inválido para CUIT %s: %s (tipo: %s)",
                    cuit,
                    persona_data,
                    type(persona_data),
                )
                raise UserError(
                    _(
                        "ARCA no devolvió datos válidos para el CUIT %s. "
                        "Esto puede ocurrir en ambiente de homologación con CUITs de prueba."
                    )
                    % cuit
                )

            # Log estructurado solo en modo debug
            if _logger.isEnabledFor(logging.DEBUG):
                dg = persona_data.get("datosGenerales") or {}
                denominacion = self._build_denominacion(dg) if isinstance(dg, dict) else None
                _logger.debug(
                    "ARCA Padrón A5 - CUIT: %s | Tipo: %s | Nombre: %s",
                    cuit,
                    dg.get("tipoPersona") if isinstance(dg, dict) else "?",
                    denominacion or "(sin nombre)",
                )

            # Transformar y parsear usando método auxiliar
            # (sin modificar el casing)
            return self._transform_and_parse_persona_data(persona_data)

        except UserError:
            # Re-raise UserError sin modificar
            raise
        except Exception as e:
            _logger.warning(
                "Error obteniendo datos ARCA para CUIT %s: %s",
                cuit,
                e,
            )
            raise UserError(error_msg % (self.name, cuit, str(e))) from e

    def l10n_ar_fiscal_ws_fe_min_ammount(self):
        for record in self:
            if record.l10n_ar_vat:
                ws = self.env.company.arca_get_connection("wsfecred")
                res = ws.call_arca_service(
                    "ConsultarMontoObligadoRecepcion",
                    {
                        "cuitConsultada": record.l10n_ar_vat,
                        "fechaEmision": fields.Date.today(),
                    },
                )
                return res
