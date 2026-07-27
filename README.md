# Odoo Argentina

Localización Argentina para Odoo Community Edition 19. Esta versión está basada en los desarrollos de
[Ingeniería ADHOC](https://github.com/ingadhoc) y cuenta con los módulos, en el directorio `adhoc-modules`, de los siguientes repositorios:

- [odoo-argentina](https://github.com/ingadhoc/odoo-argentina/tree/19.0)
- [odoo-argentina-ce](https://github.com/ingadhoc/odoo-argentina-ce/tree/19.0)
- [account-payment](https://github.com/ingadhoc/account-payment/tree/19.0)
- [account-financial-tools](https://github.com/ingadhoc/account-financial-tools/tree/19.0)

Además, en el directorio `mueve-modules` se incluye los módulos desarrollados por Mueve.

## PyAFIPws

Para poder utilizar los módulos que se conectan con los web services del ARCA (ex AFIP), se necesita tener instalada la versión actualizada de la libreria de Python 3 ***pyafipws*** (rama `py3k`) que se encuentra en: **<https://github.com/Mueve-TEC/pyafipws/tree/py3k>**

Para instalar esta libreria y el resto de dependencias puede usar el [requirements.txt](/requirements.txt) que se encuentra en el repositorio.

Instalación con pip de los requirements:

```bash
pip install -r requirements.txt
```

## Actualizar módulos de upstream (`adhoc-modules/`)

Los directorios bajo `adhoc-modules/` son **git subtrees** de repositorios
upstream de Ingeniería ADHOC. Para traer la última versión de la rama `19.0`
de cualquiera de ellos:

```bash
./scripts/pull-upstream.sh <nombre>
# <nombre> ∈ { odoo-argentina, odoo-argentina-ce, account-payment, account-financial-tools }
```

Esto ejecuta `git subtree pull --squash`, produciendo un par
"Squashed … + Merge commit …" idéntico al de la importación inicial.
Si hay conflictos (porque tenemos fixes locales sobre esos archivos),
resuélvalos normalmente, `git add` y `git commit` para terminar el merge.

## Fixes locales sobre módulos de upstream

Cuando necesitemos corregir un módulo de `adhoc-modules/` directamente
(en lugar de crear un módulo override en `mueve-modules/`), use siempre
el prefijo `[FIX-adhoc]` en el mensaje de commit:

```
[FIX-adhoc] <modulo>: <descripcion>
```

Ejemplo (rama 18.0): `[FIX-adhoc] l10n_latam_check_ux: menu view fix`.

Para auditar qué archivos de upstream tienen fixes locales pendientes sobre
el último import:

```bash
git log --grep='^\[FIX-adhoc\]' --name-only -- adhoc-modules/
```

Estos commits **no se envían a upstream**. Al hacer el siguiente
`./scripts/pull-upstream.sh`, Git hará un merge 3-way y puede pedir resolver
conflictos contra el nuevo upstream — eso es esperable y deseado: confirma
que nuestro fix sigue siendo necesario sobre la nueva base.
