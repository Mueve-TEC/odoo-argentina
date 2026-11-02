=============================
Factura Electrónica Argentina
=============================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
    :target: https://odoo-community.org/page/development-status
    :alt: Production/Stable
.. |badge2| image:: https://img.shields.io/badge/license-AGPL--3-blue.png
    :target: https://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-odoo--argentina-lightgray.png?logo=github
    :target: https://github.com/Mueve-TEC/odoo-argentina
    :alt: Mueve

|badge1| |badge2| |badge3|

Este módulo integra Odoo con los Web Services de facturación electrónica de
ARCA (ex AFIP) para emitir comprobantes desde Contabilidad. Obtiene el CAE de
los comprobantes al confirmarlos y guarda la respuesta de ARCA, incluyendo el
XML enviado y recibido y el código QR obligatorio.

Se apoya en ``l10n_ar_fiscal_ws`` para la autenticación (WSAA), los
certificados y el registro de servicios.

**Tabla de contenidos**

.. contents::
   :local:

Funcionalidades
===============

- Integración con los Web Services de ARCA:
    - ``wsfe`` (WSFEv1): factura electrónica sin detalle.
    - ``wsfex`` (WSFEXv1): factura electrónica de exportación.
    - ``wsbfe`` (WSBFE): bono fiscal con detalle.
- Configuración de diarios de Contabilidad con sistema de punto de venta
  electrónico (**Electronic Invoice - Web Service**, **Electronic Fiscal Bond -
  Web Service** y **Export Voucher - Web Service**).
- Solicitud automática del CAE al confirmar facturas y notas de crédito/débito,
  con manejo de rechazos y observaciones de ARCA.
- Generación del código QR de ARCA para comprobantes autorizados por CAE o
  CAEA.
- Asociación automática de notas de crédito y débito con el comprobante
  original (``CbtesAsoc``), incluyendo las notas generadas desde el Punto de
  Venta.
- Sincronización de la numeración con el último comprobante autorizado en ARCA.
- Soporte de comprobantes de Factura de Crédito Electrónica MiPyME (FCE), con
  opción de transmisión SCA o ADC.
- Manejo de pagos en moneda extranjera y cotización informada a ARCA.
- Validación de la *Condición frente al IVA del receptor* (RG 5616) antes de
  solicitar el CAE.
- En homologación sin certificados configurados, permite validar localmente
  los comprobantes para pruebas.
- Guarda en cada comprobante el resultado de ARCA, el mensaje, el XML de
  request/response y los campos de autorización (CAE, CAEA, vencimiento).

Instalación
===========

El módulo depende de ``l10n_ar_fiscal_ws``, ``l10n_ar`` y
``account_debit_note``. Instale y configure primero ``l10n_ar_fiscal_ws``
(certificados y conexión con ARCA).

Luego actualice la lista de aplicaciones e instale
**Factura Electrónica Argentina** desde **Aplicaciones**.

Configuración
=============

Diarios
-------

En **Contabilidad > Configuración > Diarios**, configure el diario de ventas
con el sistema de punto de venta electrónico correspondiente:

- **Electronic Invoice - Web Service** para WSFEv1.
- **Electronic Fiscal Bond - Web Service** para WSBFE.
- **Export Voucher - Web Service** para WSFEX.

El diario queda asociado automáticamente al Web Service de ARCA y expone los
botones de prueba de conexión, método *dummy*, consulta de puntos de venta y
consulta de tipos de documento.

Ajustes de la compañía
----------------------

En **Contabilidad > Configuración > Ajustes** se configuran:

- **Opción de transmisión FCE** (SCA o ADC), necesaria para los comprobantes
  MiPyME.
- **Política por defecto para pagos en moneda extranjera**.

Receptor
--------

El contacto receptor debe tener configurados el tipo y número de documento y
la *Condición frente al IVA del receptor* (responsabilidad AFIP), ya que ARCA
la exige desde la RG 5616.

Uso
===

Emitir un comprobante
---------------------

1. Crear una factura o nota de crédito/débito en un diario configurado con
   punto de venta electrónico.
2. Verificar que la fecha, el tipo de comprobante, el receptor y sus datos
   fiscales estén completos.
3. Confirmar el comprobante. El módulo solicita el CAE a ARCA y, si la
   respuesta es aceptada, publica el resultado en el chatter y deja el
   comprobante autorizado.

Si ARCA rechaza u observa el comprobante, el mensaje se informa al usuario y
queda registrado en el comprobante junto con el XML de respuesta.

Código QR
---------

Los comprobantes autorizados por CAE o CAEA muestran el campo **AFIP QR code**
con la URL que debe imprimirse en el comprobante. El QR se genera
automáticamente a partir de los datos fiscales y del código de autorización.

Notas de crédito y débito
-------------------------

Las notas de crédito y débito se asocian al comprobante original. Si el
comprobante original no tiene CAE o no tiene número de documento válido, el
módulo informa el problema antes de enviar la solicitud, para evitar consumir
un CAE que luego no pueda registrarse.

Homologación
------------

En entorno de homologación, si no hay certificados configurados, los
comprobantes se validan localmente para poder probar el circuito sin conexión
real con ARCA. El mensaje correspondiente queda registrado en el comprobante.

Bug Tracker
===========

Los errores y solicitudes se gestionan en el repositorio de GitHub
`Mueve-TEC/odoo-argentina <https://github.com/Mueve-TEC/odoo-argentina/issues>`_.

Créditos
========

Autores
-------

* Mueve (https://www.mueve.org.ar/)
* ADHOC SA
* Moldeo Interactive
* Odoo Community Association (OCA)

Mantenedores
------------

Este módulo es mantenido por Mueve.

Para contribuir a este módulo, visite
https://github.com/Mueve-TEC/odoo-argentina.
