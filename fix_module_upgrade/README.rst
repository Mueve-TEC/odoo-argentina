===========================
Fix Module Upgrade
===========================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
    :target: https://odoo-community.org/page/development-status
    :alt: Production/Stable
.. |badge2| image:: https://img.shields.io/badge/license-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-odoo--argentina-lightgray.png?logo=github
    :target: https://github.com/Mueve-TEC/odoo-argentina
    :alt: Mueve

|badge1| |badge2| |badge3|

Módulo técnico que corrige el error TypeError que ocurre al actualizar módulos en Odoo 16.0.

Características
===============

- Corrige el error: "button_immediate_upgrade() takes 1 positional argument but 2 were given"
- Se instala automáticamente
- Compatible con Odoo Community Edition 16.0

Problema Resuelto
=================

Este es un problema conocido en Odoo 16.0 donde la firma del método ``button_immediate_upgrade()`` 
no coincide con la forma en que se llama desde el frontend, causando un TypeError al intentar 
actualizar módulos desde la interfaz de aplicaciones.

Instalación
===========

Para instalar este módulo, debe seguir los siguientes pasos:

1. Descargue el módulo y colóquelo en el directorio de addons de Odoo.
2. Reinicie el servidor de Odoo.
3. El módulo se instalará automáticamente (auto_install=True).

Dependencias
============

Este módulo depende de los siguientes módulos de Odoo:

- `base`

Uso
===

Una vez instalado, el módulo funciona de forma transparente. Los usuarios pueden actualizar 
módulos desde la interfaz de aplicaciones sin encontrar el TypeError.

Créditos
========

Autor
-----

Este módulo fue desarrollado por:

- Mueve (https://www.mueve.org.ar/)

Mantenedores
------------

Este módulo es mantenido por:

- Mueve (https://www.mueve.org.ar/)
