# Migration status 18 → 19 — odoo-argentina

> Authoritative backlog for finishing the Odoo-19 migration of the modules in
> this repo. Extracted (and pruned) from the supermodule `soltec-localdev19`
> `PLAN.md`, which was deleted when the `19.0` localdev base was cleaned up;
> the full original is recoverable there with `git show ffe54b7:PLAN.md`.
>
> Verified against this tree **2026-09-22**. Update the tables when a row
> lands — do not accumulate stale rows.

## Remaining migration work

| Priority | Module                                              | Manifest     | State                                                                                                                            | Work                                                                                                     |
| -------- | --------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1        | `l10n_ar_reports` (adhoc odoo-argentina-ce)         | `16.0.1.0.0` | Genuinely unmigrated Odoo-16 code: 2 `<tree>` views, 2 `attrs=`, 6 `states=` buttons, `base64.encodestring` in `account_vat_ledger.py` | Full migration pass — biggest remaining item (this repo's README already flags it as the only unmigrated upstream module) |
| 2        | `account_financial_amount` (adhoc account-financial-tools) | `13.0.1.0.0` | One `attrs=` in `wizard/res_config_settings_views.xml`                                                                           | Inline the `attrs`, bump version                                                                         |
| 3        | `account_payment_multi` (adhoc account-payment)     | `18.0.1.1.0` | XML already list/attrs-clean                                                                                                     | Version bump only (decide: `[FIX-adhoc]` bump or leave for upstream)                                     |

**Done — do not re-do:**

- ARCA fiscal-ws polish pass (old PLAN P1–P9 / F1–F6 / T1) — merged via PR
  Mueve-TEC/odoo-argentina#2. `l10n_ar_fiscal_ws` `19.0.1.8.1`,
  `l10n_ar_fiscal_ws_fe` `19.0.1.1.0`, `l10n_ar_pos_afipws_fe` `19.0.1.0.0`;
  19 test methods across the three modules (all mocked ARCA, tagged
  `post_install` + module name).
- `l10n_ar_inflation_adjustment` → `19.0.1.0.0` (complete in `188bd2564`,
  including the xpaths / search-view `<group>` / `_read_group` follow-ups).
- `payment_sipago` migrated (separate submodule, conventional commits).
- `l10n_ar_tax_ratio` orphan copy removed from `custom-addons/`.

Conventions for the remaining rows: edit here in the submodule, `[FIX-adhoc]`
prefix for adhoc-modules in-place fixes, `[MIG]`/`[FIX]` for `mueve-modules/`,
then sync from the supermodule (`bash copy_addons.sh` + `make restart`) and
install/upgrade smoke on a scratch DB.

## Deferred (deliberately not done)

- **D1 — `migrations/` OpenUpgrade scripts.** Only fresh installs are
  supported. If a customer ever upgrades from 18.0 `l10n_ar_afipws`, table
  renames (`afipws_*` → `arcaws_*`) + `ir.model.data` xmlid renames need a
  `pre-migrate.py` with raw SQL. Do not add preemptively.
- **F6 — `en.po`.** `l10n_ar_fiscal_ws*` ship only `es.po`; generate `en.po`
  from a `.pot` only if an English UI is ever required (unlikely for an AR
  localization).
- **C1 — cosmetic `pyafipws_*` method names** (`do_pyafipws_request_cae`,
  `get_pyafipws_currency_rate`, `test_pyafipws_dummy`, …) → ARCA names.
  Only rename if no other consumer exists — grep `mueve-modules` and
  `submodules/odoo-union` first; keep XML button labels as-is.
- **C2 — POS-type codes `RAW_MAW` / `BFEWS` / `FEEWS`** (likely typos for
  `WSFE`/`WSFEX`/`WSBFE`) in `account.journal.l10n_ar_afip_pos_system`.
  Renaming selection keys requires a data migration or live values go unset.
- **Real-ARCA production homologation smoke**: padrón update on
  RM/IVARI/IVAE/CF partners, one out-invoice CAE request, "Check rate"
  button.

## Reference: real ARCA A5 response shape

Confirmed on real homologation via zeep (`serialize_object` output) — needed
by anyone touching `l10n_ar_fiscal_ws/models/res_partner.py` (this was only
ever documented in the deleted supermodule `PLAN.md`):

```
datosGenerales: {
  apellido, nombre, razonSocial (None for FISICA with apellido/nombre),
  tipoPersona ("FISICA" | "JURIDICA"), tipoClave ("CUIT"),
  idPersona (int CUIT), estadoClave ("ACTIVO"),
  mesCierre (int),
  domicilioFiscal: {
    direccion, localidad (barrio for CABA), codPostal,
    descripcionProvincia (UPPERCASE, no accents: "CORDOBA", "TUCUMAN"),
    idProvincia (int → _ARCA_PROVINCIA_ID_TO_CODE, class attr in res_partner.py),
    tipoDomicilio ("FISCAL"), tipoDatoAdicional (None), datoAdicional (None)
  },
  caracterizacion: [], dependencia: None,
  esSucesion ("NO"), fechaContratoSocial: None, fechaFallecimiento: None
}
datosMonotributo: {
  actividad: [...], actividadMonotributista: {...},
  categoriaMonotributo: {descripcionCategoria, idCategoria, idImpuesto, periodo} | {},
  componenteDeSociedad: [],
  impuesto: [{descripcionImpuesto, estadoImpuesto ("AC"|"EX"|"NA"), idImpuesto, motivo, periodo}]
}
datosRegimenGeneral: {
  actividad: [...], categoriaAutonomo: None,
  impuesto: [{...same shape as datosMonotributo.impuesto...}],
  regimen: []
}
errorConstancia:    None | {"error": "..."}
errorMonotributo:   None | {"error": "..."}
errorRegimenGeneral: None | {"error": "..."}
```

Gotchas that bit us — do not regress:

- Single-element SOAP arrays serialize as a **dict**, not a list — use the
  `_as_list` helper inside `_transform_arca_persona_to_census` for any new
  code that iterates ARCA arrays.
- State match is via `domicilioFiscal.idProvincia` (int) →
  `_ARCA_PROVINCIA_ID_TO_CODE` → ISO 3166-2:AR `code` (accent-proof). The map
  is a class attribute of `res.partner`; do not rename or remove it.
- Responsibility mapping mirrors `pyafipws.ws_sr_padron.WSSrPadronA5`
  (`32→EX, 33→NI, 34→NA, 30→S`; monotributo = category dict non-empty;
  impuestos = union of `datosMonotributo.impuesto` +
  `datosRegimenGeneral.impuesto`).
- Errors in the `error*` keys must surface as `UserError` **with their
  content** (e.g. RG 4280/18 pendiente domicilio), never the generic
  "ARCA no devolvió datos válidos" — regression test:
  `tests/test_padron_errors.py`.

## Things not to do

- Never edit `custom-addons/` in the supermodule — edit here, then
  `bash copy_addons.sh` + restart/upgrade from the supermodule.
- Do **not** import `pyafipws` / `pysimplesoap` in migrated modules — `zeep`
  only (pyafipws remains a requirements/docs dependency; the WS code paths
  were rewritten).
- Do not add new ad-hoc `cr.commit()` calls; the two existing ones (TA
  persist in `res_company.py`, CAE-success in `account_move.py`) are
  deliberate and documented in-place.
- Do not re-enable old `l10n_ar_afipws` / `l10n_ar_afipws_fe` module names —
  they no longer exist in the 19.0 re-import.
- One logical fix = one commit, `[FIX-adhoc]`/`[MIG]`/`[FIX]` prefix; push
  only when explicitly asked; never `git add -A` blindly (subtree layout —
  prefer selective adds).
