==================================
Argentina - Ajuste por Inflación
==================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-odoo--argentina-lightgray.png?logo=github
    :target: https://github.com/ingadhoc/odoo-argentina
    :alt: odoo-argentina

|badge1| |badge2| |badge3|

Módulo para el cálculo y generación del **Ajuste por Inflación Contable** 
requerido por la normativa argentina al momento del cierre del ejercicio fiscal.

**Características principales:**

* Compatible con Odoo Community Edition 16.0
* Utiliza los índices IPC publicados por INDEC
* Implementa las normas RT 6, RT 17 y RT 48 de FACPCE
* Genera automáticamente el asiento de ajuste por inflación

Marco Normativo
===============

El ajuste por inflación contable en Argentina está regulado por:

* **RT 6** (FACPCE): Estados Contables en Moneda Homogénea
* **RT 17** (FACPCE): Normas Contables Profesionales
* **RT 48** (FACPCE): Modificaciones a la RT 17 sobre inflación

Según estas normas, cuando existe un contexto de alta inflación (variación 
acumulada del IPC superior al 100% en 3 años), los estados contables deben 
expresarse en moneda homogénea de cierre.

Conceptos Clave
===============

Rubros Monetarios vs No Monetarios
----------------------------------

* **Rubros Monetarios**: Representan moneda de curso legal o derechos/obligaciones
  en moneda (caja, bancos, créditos, deudas). No se ajustan.
  
* **Rubros No Monetarios**: No representan moneda ni están determinados en moneda
  (bienes de uso, inventarios, patrimonio neto, resultados). Se ajustan.

El módulo identifica las cuentas no monetarias mediante el tag "Non Monetary"
(``l10n_ar_ux.no_monetaria_tag``).

RECPAM
------

El **Resultado por Exposición a los Cambios en el Poder Adquisitivo de la Moneda**
(RECPAM) es la contrapartida del ajuste por inflación. Representa la ganancia o 
pérdida por mantener activos/pasivos monetarios durante períodos inflacionarios.

Funcionamiento
==============

1. **Índices IPC**: El módulo incluye los índices de precios al consumidor 
   publicados por INDEC desde 2013 hasta la fecha actual.

2. **Cálculo del Ajuste**: Para cada cuenta no monetaria, se calcula:
   
   * Saldo Inicial × (Índice Cierre / Índice Apertura - 1)
   * Movimientos del Período × (Índice Cierre / Índice del Mes - 1)

3. **Generación del Asiento**: Se crea un asiento de ajuste con:
   
   * Una línea por cada cuenta ajustada
   * Contrapartida en la cuenta RECPAM

Instalación
===========

1. Copiar el módulo a la carpeta de addons
2. Actualizar la lista de aplicaciones
3. Instalar "Argentina - Ajuste por Inflación"

Dependencias:

* ``account`` (Contabilidad)
* ``l10n_ar`` (Localización Argentina)

**Nota:** Este módulo es completamente independiente y no requiere módulos 
Enterprise ni otros módulos de la localización argentina como ``l10n_ar_ux``.
Si ``l10n_ar_ux`` está instalado, el módulo es compatible y puede usar su tag 
"Non Monetary" existente.

Uso
===

Configuración
-------------

1. **Verificar Cuentas No Monetarias**:
   
   Ir a Contabilidad > Configuración > Plan Contable
   
   Al instalar el módulo, automáticamente se asigna el tag "No Monetaria" 
   a las cuentas que corresponden según su tipo (activos fijos, patrimonio, 
   resultados, etc.).
   
   Para asignar manualmente el tag a cuentas adicionales:
   
   * Seleccionar las cuentas en la vista de lista
   * Usar la acción "Asignar Tag No Monetaria a Cuentas"
   
   Para asignar automáticamente a todas las cuentas de la compañía:
   
   * Ejecutar la acción "Asignar Tag No Monetaria a Todas las Cuentas"

2. **Verificar Índices IPC**:
   
   Ir a Contabilidad > Configuración > Ajuste por Inflación > Índices IPC
   
   El módulo incluye índices históricos. Agregar índices faltantes si es necesario.

3. **Crear o Identificar Cuenta RECPAM**:
   
   Esta es la cuenta donde se registrará el resultado por inflación.
   Usualmente es una cuenta de resultados financieros. En nuestra implementación es la cuenta **"5.6.1.01.070 R.E.C.P.A.M."**.

Generar Ajuste por Inflación
----------------------------

1. Ir a Contabilidad > Acciones > Generar Ajuste por Inflación
2. Seleccionar el período del ejercicio fiscal
3. Seleccionar el diario y la cuenta RECPAM
4. Indicar si hay asientos de cierre/apertura a excluir
5. Click en "Vista Previa" para revisar las líneas de ajuste
6. Click en "Generar Asiento" para crear el asiento contable

Créditos
========

Autores
-------

* ADHOC SA
* [Fundación Mueve](https://mueve.org.ar)

Contribuidores
--------------

* Ezequiel Ludueña

Mantenedores
------------

Este módulo es mantenido por Fundación Mueve.


