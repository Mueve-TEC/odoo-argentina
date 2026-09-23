# POS invoicing (Argentina) + ARCA — operational context

> Follow-up doc for agents/devs working on **POS + ARCA electronic invoicing**
> in this repo (modules `l10n_ar_pos_afipws_fe`, `l10n_ar_fiscal_ws_fe`).
> Salvaged from the supermodule `POS_context.md`, deleted in the `19.0`
> localdev cleanup — full original: `git show ffe54b7:POS_context.md` (repo
> `soltec-localdev-odoo19`). Pruned 2026-09-22; last live verification
> **2026-08-10**.

## Status

- Normal POS invoicing → ARCA CAE **works on homologation** (2026-08-10):
  two `FA-B` invoices returned `afip_result=A` with CAE
  `86320746773270` / `86320746774506` on DB `admin1`.
- **Open:** the refund path (`reversed_entry_id` credit note) has **not**
  been re-tested live since the totals fix — first thing to verify in the
  next homologation session.
- Reference working setup (reuse it):
  - DB `admin1`; company "My Company" (`partner_id=1`, country AR,
    resp. type 1 = IVA Responsable Inscripto, VAT `20431432227`)
  - POS config 2 "nueva": `invoice_journal_id = 11` ("Factura POS"),
    PtoVta 6, `arcaws=wsfe`, homologation certs "Using DB certificates",
    `arcaws.env.type = homologation`; cert alias `ARCA WS`
  - Verified results: move 16 `FA-B 00006-00000001` total 169.40 → CAE
    `86320746773270`; move 18 `FA-B 00006-00000002` total 6.17 → CAE
    `86320746774506` (both `afip_result=A`), POS orders `261-2-000001/2`,
    session 6.

## What `l10n_ar_pos_afipws_fe` actually does

Single override `pos.order._prepare_invoice_vals()`:

- For POS **refunds** of ARCA-authorized invoices (`journal_id.arcaws` +
  `afip_auth_code`, AR company, `out_invoice`), sets `reversed_entry_id` to
  the original invoice; raises `UserError` if more than one such invoice.
- **Not needed** for normal (non-refund) POS invoicing — that path is core
  `point_of_sale` + `l10n_ar_fiscal_ws_fe` (ARCA CAE on `_post`).

## ARCA error dictionary (learned the hard way)

| Code            | Meaning                                                                                                                        | Fix / unblock                                                                                                                                                                                                                                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `10048` + `10018` | Totals mismatch: `ImpTotal` ≠ sum of components; `Iva`/`AlicIva` mandatory when `ImpIVA=0` (Id iva=3)                          | Root cause was `_l10n_ar_get_amounts()` called **without `base_lines`** → every ARCA amount came back 0 while `ImpTotal` read `amount_total`. Fixed in `926dc855`: pass `inv._get_rounded_base_and_tax_lines()[0]` as `base_lines`. **Not** a tax/config/B2C issue — AR B invoices do report IVA (included in price).                                                       |
| `10016`         | "El numero o fecha del comprobante no se corresponde con el proximo a autorizar" — a PtoVta was authorized with a **future** `invoice_date`, so earlier-dated orders are rejected | Unblock: `date_order` ≥ last authorized date, wait it out, or use a fresh PtoVta / doc-type. PtoVta 6 ("nueva") was a clean point of sale and never hit this.                                                                                                                                                                                                            |
| `10043`         | `ImpTotConc` must be 0 for type-C vouchers — the invoice carried base taxed with **"IVA No Gravado"** (AFIP code `1`). Real root cause was **config**: company `IVA Sujeto Exento` (issues FA-C) but products still had demo taxes (**IVA 21%** on 38 templates + No Gravado on "Acoustic Bloc Screens", DB `pos_fix`) | Config fix: strip VAT-type sale taxes from products of a C-issuer (done in `pos_fix` 2026-09-23, 39 templates → CAE `86380921654850` on FA-C 00004-00000001). Code-side guard: `l10n_ar_fiscal_ws_fe` now raises a **clear UserError before any ARCA call** (`account_move._l10n_ar_check_letter_c_amounts`) naming the offending amounts + the company responsibility type. |
| doc-type rollback | Company resp. type **5 = Consumidor Final** maps to `[]` issued letters in `l10n_ar._get_journal_letter` → sale journal has no document types → every POS invoice rolls back | Set resp. type 1 (Responsable Inscripto) or 6 on the company. (DB `admin` "ads" hit this; `admin1` is resp. type 1 and works.)                                                                                                                                                                                                                                            |

Also: ARCA rejections live in `Errors.Err`, **not only** in
`FeDetResp...Observaciones` — `request_invoice_authorization`'s
`response_dict` extracts `afip_errors` from `Errors.Err`; the invoice combines
observations + errors into `afip_message` and logs at ERROR (previously the
diagnostic was lost because the `UserError` rolled back the write).
**Data change ⇒ requires `-u l10n_ar_fiscal_ws_fe`** or the DB's
`response_dict` stays stale.

## Homologation health check

```bash
# WSDL reachable? (expect 200)
docker compose exec web python3 -c "import urllib.request;
print(urllib.request.urlopen('https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL', timeout=15).status)"
# FEDummy OK?
docker compose exec web python3 -c "
from zeep import Client
print(Client('https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL').service.FEDummy())"
```

Endpoints: homologation `wswhomo.afip.gov.ar` / `fwshomo.afip.gov.ar`
(`wsfecred`), production `serviciosjava.afip.gob.ar` — the `wsfecred`
`arcaws` records already carry both URLs.

## Run the tests

```bash
docker compose exec web odoo \
  --addons-path=/mnt/custom-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -d test_pos --db_host=db --db_user=odoo --db_password=odoo \
  --test-enable --test-tags=/l10n_ar_pos_afipws_fe,/l10n_ar_fiscal_ws_fe \
  -u l10n_ar_pos_afipws_fe,l10n_ar_fiscal_ws_fe \
  --stop-after-init --http-port=8099 --log-level=info
```

Expect `0 failed, 0 error` — 5 tests: 3 POS refund (`test_pos_order.py`) +
2 currency-rate (`test_currency_rate.py`). `test_pos` = fresh DB with the
full AR stack; its company is **US by default** — `test_pos_order.py` sets
`company.country_id = base.ar` and the sale journal to `RAW_MAW` in
`setUpClass`. `--http-port=8099` is required while the web container owns
8069.

Manual E2E — shell repro of the posting path:

```bash
docker compose exec web odoo shell -d admin1 \
  --addons-path=/mnt/custom-addons,/usr/lib/python3/dist-packages/odoo/addons \
  --db_host=db --db_user=odoo --db_password=odoo --no-http <<'EOF'
inv = env['account.move'].browse(12)  # draft FA-B, no CAE
inv.invoice_date = '2026-08-10'
try:
    inv._post()
    env.cr.commit()
    print('POST OK', inv.name, inv.afip_result, inv.afip_auth_code)
except Exception as e:
    env.cr.rollback()
    print('EXCEPTION:', repr(e))
EOF
```

Refund check after a live refund:

```bash
docker compose exec db psql -U odoo -d admin1 -x \
  -c "SELECT id, name, move_type, reversed_entry_id, afip_auth_code FROM account_move WHERE move_type='out_refund' ORDER BY id DESC LIMIT 1;"
```

Note: a draft move created *before* the totals fix stays draft (its lines
never reflowed taxes) — always validate with a **fresh POS order**.

## Key provenance (commits in this repo)

| SHA        | What                                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------------------------------- |
| `22ad61b6d` | `[MIG]` `l10n_ar_pos_afipws_fe` → Odoo 19 + refund tests                                                          |
| `a1e47e998` | surface ARCA `<Errors>` on rejected CAE (`afip_errors` extraction + `afip_message` + ERROR-level logging)          |
| `926dc855`  | pass `base_lines` to `_l10n_ar_get_amounts` (fixes 10048/10018 — every invoice was sending 0 amounts)               |
| `6ec75d267` | hard `UserError` on invalid `arcaws.env.type` (live env switch without restart — see supermodule AGENTS gotcha)    |

## Environment gotchas

- `custom-addons/` in the supermodule is **generated + gitignored**: edit
  here in the submodule, `bash copy_addons.sh`, restart the web service.
- Shell/CLI must pass the full
  `--addons-path=/mnt/custom-addons,/usr/lib/python3/dist-packages/odoo/addons`
  and `-d <db> --db_host=db --db_user=odoo --db_password=odoo`; without the
  addons path, custom modules are "not installable".
- In-place adhoc fixes use the `[FIX-adhoc] <module>: <desc>` commit prefix.
- Always use selective `git add <paths>` inside this repo (subtree layout —
  never `git add -A` blindly). Commit/push only when explicitly asked.
