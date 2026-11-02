=========================================
Módulo Base para los Web Services de ARCA
=========================================

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

Este módulo provee la infraestructura común para conectarse a los Web Services
de ARCA (ex AFIP) desde Odoo. Centraliza el registro de servicios y métodos, la
autenticación contra el WSAA, la administración de certificados y la consulta
del padrón A5 de constancia de inscripción.

El resto de los módulos de facturación electrónica (``l10n_ar_fiscal_ws_fe`` y
``l10n_ar_pos_afipws_fe``) se apoyan en esta base para realizar sus llamadas.

**Tabla de contenidos**

.. contents::
   :local:

Funcionalidades
===============

- Registro de Web Services de ARCA (``arcaws``) con URL de producción y de
  homologación por servicio.
- Registro de métodos por servicio (``arcaws.method``) con plantillas de
  request/response evaluadas con ``safe_eval``, de modo que los cambios de
  estructura se administran como datos y no como código.
- Autenticación contra el WSAA (``LoginCms``): generación del ticket de acceso
  (token y sign), su almacenamiento por compañía y su reutilización hasta el
  vencimiento.
- Administración de alias de certificado y certificados:
    - Generación de clave privada y de Certificate Signing Request (CSR).
    - Descarga del CSR para firmarlo en ARCA.
    - Carga del certificado firmado mediante un asistente.
    - Estados *Draft*, *Confirmed* y *Cancelled* con validación del certificado.
- Selección del entorno de ejecución (producción u homologación) por parámetro
  del sistema o por configuración del servidor.
- Actualización de datos de contactos desde el padrón A5 de ARCA, con
  comparación de valores y selección de campos a actualizar.
- Soporte multi-compañía para certificados, conexiones y reglas de acceso.

Instalación
===========

El módulo depende de las siguientes bibliotecas de Python:

- ``zeep`` (cliente SOAP)
- ``OpenSSL`` (``pyOpenSSL``)
- ``cryptography`` (generación de claves y CSR)

Instalarlas, por ejemplo, con:

.. code-block:: bash

   pip install zeep pyOpenSSL cryptography

Luego actualice la lista de aplicaciones e instale
**Modulo Base para los Web Services de ARCA** desde **Aplicaciones**.

Configuración
=============

Certificados
------------

Ir a **Contabilidad > Configuración > AFIP > Certificates**.

1. Crear un alias de certificado indicando compañía, tipo (producción u
   homologación) y datos del titular.
2. Generar el CSR y descargarlo.
3. Firmar el CSR en el sitio de ARCA y subir el certificado resultante.
4. Confirmar el alias y el certificado.

También se pueden usar certificados provistos por archivo de configuración de
Odoo. Si no hay un certificado confirmado en la base, el módulo busca las rutas
``arca_prod_pkey_file`` / ``arca_prod_cert_file`` (producción) y
``arca_homo_pkey_file`` / ``arca_homo_cert_file`` (homologación) en el
archivo de configuración del servidor.

Entorno de ejecución
--------------------

El entorno se define, en orden de prioridad, por:

1. El parámetro del sistema ``arcaws.env.type``, configurable desde
   **Contabilidad > Configuración > Ajustes** (valores ``production`` u
   ``homologation``).
2. La opción ``server_mode`` del archivo de configuración de Odoo.

Un valor inválido en ``arcaws.env.type`` genera un error explícito en lugar de
caer silenciosamente en el otro entorno. El cambio de entorno se aplica en
caliente, sin reiniciar el servidor.

Conexiones
----------

Ir a **Contabilidad > Configuración > AFIP > Connections** para consultar los
tickets de acceso emitidos por el WSAA. Las conexiones vencidas se eliminan
automáticamente por la tarea de autovacuum.

Web Services
------------

Ir a **Contabilidad > Configuración > AFIP > Arca WebService** para revisar los
servicios y métodos disponibles. El módulo carga, entre otros:

- ``LoginCms`` (WSAA).
- ``ws_sr_constancia_inscripcion`` (padrón A5).
- ``wsfecred`` (factura de crédito electrónica MiPyME).

Cada servicio incluye métodos de prueba (``dummy``), consulta de puntos de
venta y tipos de comprobante.

Actualización desde el padrón A5
--------------------------------

En la ficha de un contacto con CUIT se puede ejecutar el asistente de
actualización desde el padrón A5. El asistente compara los datos actuales con
los devueltos por ARCA y permite elegir qué campos actualizar antes de
confirmar.

Uso
===

Este módulo es una base técnica: la operatoria de facturación se realiza desde
los módulos que dependen de él. Sin embargo, expone utilidades de diagnóstico:

- Probar la conexión al Web Service.
- Ejecutar el método *dummy* del servicio.
- Consultar puntos de venta y tipos de documento habilitados.
- Consultar el último comprobante autorizado (usado para la numeración).

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
