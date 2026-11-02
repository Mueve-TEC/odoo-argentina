==================================================
Punto de venta - Factura Electrónica Argentina
==================================================

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

Este módulo conecta el Punto de Venta de Odoo con la facturación electrónica
de ARCA provista por ``l10n_ar_fiscal_ws_fe``. Permite emitir los comprobantes
del POS contra los Web Services de ARCA y asegura que las devoluciones generen
notas de crédito correctamente asociadas al comprobante original.

**Tabla de contenidos**

.. contents::
   :local:

Funcionalidades
===============

- Emisión de comprobantes del Punto de Venta a través de los Web Services de
  facturación electrónica de ARCA.
- Opción **Invoice by default** en la configuración del POS: las órdenes nuevas
  se marcan como *To invoice* por defecto, y el cajero puede desactivarlo en la
  pantalla de pago.
- Vinculación de las devoluciones del POS con la factura electrónica original:
  la nota de crédito se crea con el comprobante original como referencia
  (``reversed_entry_id``), de modo que ARCA recibe la asociación
  correspondiente.
- Mensaje de error claro cuando la factura electrónica original con CAE no se
  encuentra: no se permite emitir una nota de crédito sin la referencia
  obligatoria.
- Validación de que solo se devuelva una factura por vez.

Instalación
===========

El módulo depende de ``l10n_ar_fiscal_ws_fe`` y ``point_of_sale``. Instale y
configure primero ``l10n_ar_fiscal_ws`` y ``l10n_ar_fiscal_ws_fe``.

Luego actualice la lista de aplicaciones e instale
**Punto de venta Factura Electrónica Argentina** desde **Aplicaciones**.

Configuración
=============

Factura por defecto
-------------------

Ir a **Punto de Venta > Configuración > Puntos de Venta**, abrir el punto de
venta y activar la opción **Invoice by default**. Con la opción activa, cada
orden nueva se marca como *To invoice* por defecto; el cajero puede
desactivarla en la pantalla de pago si el cliente no requiere factura.

Diario y punto de venta electrónico
-----------------------------------

El punto de venta debe usar un diario configurado con el sistema de punto de
venta electrónico de ARCA (ver ``l10n_ar_fiscal_ws_fe``).

Uso
===

Ventas
------

Al cobrar una orden con la opción de facturación activa, el POS genera la
factura y solicita el CAE a ARCA a través de ``l10n_ar_fiscal_ws_fe``.

Devoluciones
------------

Al realizar una devolución desde el POS, el módulo busca la factura
electrónica original (con CAE) y la asocia a la nota de crédito. Si el
comprobante original no se encuentra, la operación se detiene con un mensaje
que indica que la nota de crédito debe referenciar la factura original.

Si se intenta devolver más de una factura a la vez, el módulo informa que solo
se puede devolver una factura por operación.

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
* Filoquin

Mantenedores
------------

Este módulo es mantenido por Mueve.

Para contribuir a este módulo, visite
https://github.com/Mueve-TEC/odoo-argentina.
