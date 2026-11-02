===================================
Argentina - Ajuste por Inflación
===================================

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

Módulo para el cálculo y la generación del **Ajuste por Inflación Contable**
requerido por la normativa argentina al cierre del ejercicio fiscal. Utiliza
los índices IPC publicados por INDEC y genera el asiento de ajuste con la
contrapartida en la cuenta RECPAM.

**Tabla de contenidos**

.. contents::
   :local:

Marco normativo
===============

El ajuste por inflación contable en Argentina está regulado por:

* **RT 6** (FACPCE): Estados Contables en Moneda Homogénea.
* **RT 17** (FACPCE): Normas Contables Profesionales.
* **RT 48** (FACPCE): Modificaciones a la RT 17 sobre inflación.

Según estas normas, cuando existe un contexto de alta inflación (variación
acumulada del IPC superior al 100% en tres años), los estados contables deben
expresarse en moneda homogénea de cierre.

Conceptos clave
===============

Rubros monetarios y no monetarios
---------------------------------

* **Rubros monetarios**: representan moneda de curso legal o derechos y
  obligaciones en moneda (caja, bancos, créditos, deudas). No se ajustan.
* **Rubros no monetarios**: no representan moneda ni están determinados en
  moneda (bienes de uso, inversiones permanentes, intangibles, inventarios,
  patrimonio neto y resultados). Se ajustan.

El módulo identifica las cuentas no monetarias con el tag **"No Monetaria
(Ajustable por Inflación)"** (``l10n_ar_inflation_adjustment.non_monetary_account_tag``).
Si el módulo ``l10n_ar_ux`` está instalado, se mantiene compatibilidad con su
tag ``l10n_ar_ux.no_monetaria_tag`` como respaldo.

RECPAM
------

El **Resultado por Exposición a los Cambios en el Poder Adquisitivo de la
Moneda** (RECPAM) es la contrapartida del ajuste por inflación. Representa la
ganancia o pérdida por mantener activos y pasivos monetarios durante períodos
inflacionarios.

Funcionalidades
===============

* Compatible con Odoo Community 19.0.
* Índices IPC de INDEC desde enero de 2013 hasta marzo de 2026, con variación
  mensual e interanual calculadas.
* Cálculo del ajuste de saldos iniciales y de los movimientos del período.
* Asistente con vista previa de las líneas de ajuste antes de generar el
  asiento.
* Generación del asiento contable en el diario seleccionado, con contrapartida
  en la cuenta RECPAM.
* Detección de índices faltantes y advertencias antes de confirmar.
* Opción para excluir asientos de cierre y de apertura del cálculo.
* Acciones de servidor para asignar o quitar el tag de cuenta no monetaria,
  tanto sobre las cuentas seleccionadas como sobre todas las cuentas de la
  compañía.

Instalación
===========

1. Copie el módulo en un directorio de addons de Odoo.
2. Reinicie el servidor de Odoo.
3. Vaya a **Aplicaciones**, actualice la lista y busque **Argentina - Ajuste
   por Inflación**.
4. Haga clic en **Instalar**.

Dependencias
============

Este módulo depende de los siguientes módulos de Odoo:

* ``account`` (Contabilidad)
* ``l10n_ar`` (Localización Argentina)

**Nota:** no requiere módulos Enterprise ni ``l10n_ar_ux``. Si ``l10n_ar_ux``
está instalado, el módulo es compatible y reutiliza su tag de cuenta no
monetaria como respaldo.

Configuración
=============

Cuentas no monetarias
---------------------

Ir a **Contabilidad > Configuración > Plan Contable**.

Al instalar el módulo, se puede asignar automáticamente el tag **"No
Monetaria"** a las cuentas que corresponden según su tipo (activos no
corrientes, activos fijos, patrimonio, ingresos y gastos).

Para asignarlo manualmente:

1. Seleccionar las cuentas en la vista de lista.
2. Usar la acción **Asignar Tag "No Monetaria" a Cuentas**.

También existe la acción **Asignar Tag "No Monetaria" a Todas las Cuentas**
para procesar todas las cuentas de la compañía, y **Quitar Tag "No Monetaria"
de Cuentas** para revertirlo.

El campo **Ajustable por Inflación** de la cuenta se calcula a partir de este
tag. Si el tag no existe, se usa como respaldo el tipo de cuenta.

Índices IPC
-----------

Ir a **Contabilidad > Configuración > Ajuste por Inflación > Índices IPC
(INDEC)**.

El módulo incluye los índices históricos. Si falta un período, agregue el
índice correspondiente antes de generar el ajuste; el asistente advierte sobre
índices faltantes.

Cuenta RECPAM
-------------

Defina la cuenta donde se registrará el resultado por inflación. Habitualmente
es una cuenta de resultados financieros.

Permisos
--------

La lectura de los índices está disponible para usuarios de contabilidad; la
creación, edición y eliminación de índices y el asistente de ajuste requieren
el grupo de administración contable.

Uso
===

1. Ir a **Contabilidad > Generar Ajuste por Inflación**.
2. Seleccionar el período del ejercicio fiscal (**Fecha Desde** y **Fecha
   Hasta**).
3. Seleccionar el diario y la cuenta RECPAM.
4. Indicar si hay asientos de cierre o de apertura que deban excluirse.
5. Verificar los índices de apertura y cierre y el factor de ajuste calculado.
6. Presionar **Vista Previa** para revisar las líneas de ajuste.
7. Presionar **Generar Asiento** para crear el asiento contable.

Problemas conocidos / Roadmap
=============================

* Los índices IPC incluidos en los datos del módulo llegan hasta marzo de
  2026; los períodos posteriores deben cargarse manualmente.
* El cálculo sigue las normas contables argentinas y no reemplaza la revisión
  profesional del cierre.

Bug Tracker
===========

Los errores y solicitudes se gestionan en el repositorio de GitHub
`Mueve-TEC/odoo-argentina <https://github.com/Mueve-TEC/odoo-argentina/issues>`_.

Créditos
========

Autor
-----

Este módulo fue desarrollado por:

* Mueve (https://www.mueve.org.ar/)
* ADHOC SA

Contribuidores
--------------

* Ezequiel Ludueña (https://github.com/ezeluduena)

Mantenedores
------------

Este módulo es mantenido por:

* Mueve (https://www.mueve.org.ar/)

Para contribuir a este módulo, visite
https://github.com/Mueve-TEC/odoo-argentina.
