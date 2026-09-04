# PLAN — Create the `19.0` branch of `odoo-argentina`

> **Scope of this document:** set up the `19.0` branch of the
> `Mueve-TEC/odoo-argentina` repo using **git subtree** to vendor four upstream
> ingadhoc repos, plus a small helper script and workflow docs. The **supermodule**
> (`soltec-localdev-odoo19`) is **out of scope** here.
>
> **Post-script (later addition):** a **fifth** upstream subtree,
> `adhoc-modules/account-invoicing` (ingadhoc `account-invoicing`, branch `19.0`),
> was added afterwards to provide `account_background_post` (a dependency of the
> vendored `account_ux`) — see the "5th subtree" note in Step 3.
>
> **Target executor:** another LLM / developer with write access to
> `Mueve-TEC/odoo-argentina`. Read this whole file once before running anything.

---

## 0. Context (why subtree, not submodules / worktrees)

This repo (`Mueve-TEC/odoo-argentina`) bundles the Argentine localization for
Odoo CE. Its `18.0` branch already uses **git subtree** to vendor upstream
ingadhoc repos under `adhoc-modules/`:

```
odoo-argentina/                 ← this repo (branch: 18.0 today, 19.0 target)
├── adhoc-modules/              ← vendored upstream repos (git subtree)
│   ├── odoo-argentina/          ← from ingadhoc/odoo-argentina
│   ├── odoo-argentina-ce/       ← from ingadhoc/odoo-argentina-ce
│   ├── account-payment/         ← from ingadhoc/account-payment
│   └── account-financial-tools/ ← from ingadhoc/account-financial-tools
├── mueve-modules/             ← Mueve's own Odoo modules (developed HERE, only home)
├── oca_dependencies.txt        ← pristine OCA repos (partner-contact, reporting-engine)
├── requirements.txt
└── README.md / README.rst / LICENSE / .gitignore
```

On `18.0` the subtree fingerprint is visible in the log:
```
9fe78ba Merge commit 'b338f553…' as 'adhoc-modules/account-payment'
b338f55 Squashed 'adhoc-modules/account-payment/' content from commit 7c413b4a
```

**Why keep subtree for 19.0** (decision already made — do not relitigate):

- We **sometimes edit upstream files in place** (e.g. 18.0 commit `e30737a`
  `[FIX] l10n_latam_check_ux: menu view fix`) but **never push those fixes
  upstream** and want to **keep pulling upstream updates**.
- Git **submodules** would require every local-only patch to live as a commit
  reachable from *some* remote (a fork). We have no fork → submodule pin would
  be unreachable for other clones / silently dropped on update. Rejected.
- Git **subtree** is purpose-built for "vendor, patch locally, never push back,
  re-merge upstream as it advances". It keeps a single self-contained clone
  (one `git clone` = full localization), which is a hard requirement here.

So: **same mechanism as 18.0, tidied up.** The only structural additions are a
`scripts/pull-upstream.sh` helper and README workflow docs + a commit-message
convention for local upstream fixes.

---

## 1. Preconditions — verify before doing anything

Run these from **inside** `submodules/odoo-argentina/` (the odoo-argentina
repo), NOT the supermodule.

```bash
# 1a. Confirm we are in the right repo.
git remote -v            # => origin  git@github.com:Mueve-TEC/odoo-argentina.git
git rev-parse --abbrev-ref HEAD   # => 18.0

# 1b. Clean working tree (no uncommitted/untracked surprises).
git status --short --untracked-files=all    # must be empty

# 1c. Up to date with our origin.
git fetch origin
git status -sb            # 18.0 should match origin/18.0

# 1d. The four upstream ingadhoc repos DO have a 19.0 branch (read-only check).
for r in odoo-argentina odoo-argentina-ce account-payment account-financial-tools; do
  printf '%-28s ' "ingadhoc/$r:"
  git ls-remote --heads "https://github.com/ingadhoc/$r.git" 19.0 | awk '{print $1}'
done
```

**Expected:** each line prints a 40-char SHA. (SHAs at plan-authoring time, for
reference only — the executor will get whatever is current:
`ingadhoc/odoo-argentina` ~`96e3e34`, `odoo-argentina-ce` ~`1d80627`,
`account-payment` ~`ab414f4`, `account-financial-tools` ~`7a5fc51`.)

If any precondition fails, **stop** and fix before continuing. In particular,
if any upstream has no `19.0` branch yet, drop just that one from the `subtree
add` list in Step 3 and note it in the final summary (do not invent a branch).

---

## 2. Create the `19.0` branch (branched from `18.0`)

Branada from 18.0 so we inherit `mueve-modules/`, `requirements.txt`,
`oca_dependencies.txt`, `.gitignore`, etc.

```bash
git checkout 18.0
git pull --ff-only           # if already up to date, this is a no-op

# Create and switch to 19.0.
git checkout -b 19.0
```

> Note: `mueve-modules/l10n_ar_inflation_adjustment` currently holds **Odoo-18**
> code. Migrating it to Odoo-19 is **separate work, out of scope for this plan**
> (see Step 7). Structurally it stays in place.
>
> **Post-script (2026-09-04 update):** the mechanical view migration of
> `l10n_ar_inflation_adjustment` has since been done on `19.0` (commits
> `[MIG] … updating views syntax for odoo 18` and later: `<list>` views, inline
> `invisible`, `_post_init_hook(env)`). What remains is final Odoo-19
> validation + 3 code fixes (broken xpaths vs. Odoo-19 core account views,
> banned `<group>` in the index search view, deprecated `read_group` in the
> wizard) — see the supermodule `soltec-localdev-odoo19/PLAN.md`
> "Remaining migration work" for the authoritative list.

---

## 3. Re-import the four upstream repos at 19.0 (git subtree add)

First drop the 18.0 adhoc subtrees so the new ones land clean on the latest
upstream `19.0` (avoids attempting a messy 18.0→19.0 upstream merge):

```bash
git rm -r adhoc-modules
git commit -m "[REF] drop 18.0 adhoc-modules subtrees; re-import at 19.0 in next commits"
```

Then add each upstream's `19.0` branch as a subtree. **One command per repo**;
each creates a "Squashed …" + "Merge commit …" pair (exactly like the 18.0
history). URLs use HTTPS so the executor doesn't need SSH keys for the read-only
fetch:

```bash
git subtree add --prefix=adhoc-modules/odoo-argentina            https://github.com/ingadhoc/odoo-argentina.git            19.0
git subtree add --prefix=adhoc-modules/odoo-argentina-ce         https://github.com/ingadhoc/odoo-argentina-ce.git         19.0
git subtree add --prefix=adhoc-modules/account-payment          https://github.com/ingadhoc/account-payment.git            19.0
git subtree add --prefix=adhoc-modules/account-financial-tools  https://github.com/ingadhoc/account-financial-tools.git    19.0
```

Expected per command: a `Squashed 'adhoc-modules/<repo>/' content from commit …`
commit, then a `Merge commit '…' as 'adhoc-modules/<repo>'` merge commit, and a
non-empty `adhoc-modules/<repo>/` tree afterwards.

If a single `subtree add` reports a conflict or an already-existing prefix,
**stop**: that means Step 1b/Step 2 was skipped or the prefix wasn't cleared.
Resolve by re-running `git rm -r adhoc-modules/<repo>` + commit, then retry just
that repo.

### 3.1 Sanity-check the result

> **5th subtree (added later, after this plan's steps ran):**
> `git subtree add --prefix=adhoc-modules/account-invoicing https://github.com/ingadhoc/account-invoicing.git 19.0 --squash`
> (squash add, matching `pull-upstream.sh`). Motivación: el `account_ux` ya
> vendido depende de `account_background_post`, que no estaba disponible en el
> árbol; `account-invoicing` lo aporta. Todos sus módulos dependen solo de
> módulos Community (`account`, `sale`, `website_sale`,
> `l10n_latam_invoice_document`, `account_ux`).
>
> `account-invoicing` was **also added to `scripts/pull-upstream.sh` URLS** (so
> the script now accepts 5 keys, not the 4 shown in section 4).

```bash
ls adhoc-modules          # => 5 dirs: odoo-argentina, odoo-argentina-ce, account-payment, account-financial-tools, account-invoicing
git log --oneline -12     # should show "Merge commit … as 'adhoc-modules/…'" pairs on top of the [REF] drop commit
# Confirm a known module is present in each:
ls adhoc-modules/odoo-argentina            | head
ls adhoc-modules/odoo-argentina-ce         | head
ls adhoc-modules/account-payment           | head
ls adhoc-modules/account-financial-tools   | head
```

---

## 4. Add `scripts/pull-upstream.sh` (the only new artifact)

Create `scripts/pull-upstream.sh` with this exact content:

```bash
#!/usr/bin/env bash
# pull-upstream.sh — re-pull latest 19.0 from an ingadhoc repo into adhoc-modules/<name>.
#
# Usage:
#   ./scripts/pull-upstream.sh <name>
#       <name> ∈ { odoo-argentina, odoo-argentina-ce, account-payment, account-financial-tools }
#
# Runs `git subtree pull --squash`, i.e. one "Squashed …" + one "Merge commit …"
# pair on top of HEAD — identical flow to the initial `git subtree add`.
#
# If a pull conflicts (because we have local in-place fixes on those files),
# resolve the conflicts normally, `git add`, and `git commit` to finish the merge.
#
# Commit message convention for local upstream fixes (see README):
#   "[FIX-adhoc] <module>: <description>"
set -euo pipefail

declare -A URLS=(
  [odoo-argentina]="https://github.com/ingadhoc/odoo-argentina.git"
  [odoo-argentina-ce]="https://github.com/ingadhoc/odoo-argentina-ce.git"
  [account-payment]="https://github.com/ingadhoc/account-payment.git"
  [account-financial-tools]="https://github.com/ingadhoc/account-financial-tools.git"
)

BRANCH="19.0"
NAME="${1:-}"
if [[ -z "$NAME" ]] || [[ -z "${URLS[$NAME]:-}" ]]; then
  echo "Usage: $0 <one of: ${!URLS[*]}>" >&2
  exit 1
fi
PREFIX="adhoc-modules/$NAME"
URL="${URLS[$NAME]}"

echo "==> git subtree pull --squash --prefix=$PREFIX $URL $BRANCH"
git subtree pull --prefix="$PREFIX" "$URL" "$BRANCH" --squash
```

Write the file with **exactly** those four keys (no extras):

```bash
mkdir -p scripts
# (write scripts/pull-upstream.sh with the block above)
chmod +x scripts/pull-upstream.sh
```

Verify it parses and lists usage:

```bash
bash -n scripts/pull-upstream.sh        # syntax check (no output = OK)
./scripts/pull-upstream.sh              # should print "Usage: ./scripts/pull-upstream.sh <…>" and exit 1
```

---

## 5. Document the workflow in `README.md`

The 18.0 `README.md` already documents the structure. Replace its intro so it
applies to 19.0, then **append** the two new sections below (translated to
Spanish to match the existing README voice — the executor should keep the
surrounding file's language **Spanish**; the English below is a spec for what
to write):

### 5.1 Update the intro
Change *"Localización Argentina para Odoo Community Edition **18**."* to
**19**, and keep the list of upstream repos pointing at their `/tree/19.0`
URLs (same four as 18.0, just on branch 19.0).

### 5.2 Append these new sections (write them in Spanish)

```markdown
## Actualizar módulos de upstream (`adhoc-modules/`)

Los directorios bajo `adhoc-modules/` son **git subtrees** de repositorios
upstream de Ingeniería ADHOC. Para traer la última versión de la rama `19.0`
de cualquiera de ellos:

```bash
./scripts/pull-upstream.sh <nombre>
# <nombre> ∈ { odoo-argentina, odoo-argentina-ce, account-payment, account-financial-tools, account-invoicing }
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
```

---

## 6. Commit the docs + helper (single commit on 19.0)

```bash
git add scripts/pull-upstream.sh README.md PLAN.md
git commit -m "[DOC] add upstream-update workflow (subtree pull helper + README)"
```

(Committing `PLAN.md` keeps provenance of how 19.0 was set up. It's optional —
if you'd rather not keep a process doc in the repo long-term, drop `PLAN.md`
from the `git add` and leave it untracked, then delete it after Step 8.)

---

## 7. (Out of scope — flagged for later) Migrate `mueve-modules/*` to Odoo 19

`mueve-modules/l10n_ar_inflation_adjustment` is Odoo-18 code carried over from
the 18.0 branch in Step 2. It needs actual Odoo-version migration (view syntax
`tree`→`list`, `attrs`→inline `invisible`, compute/store rules, `_post_init_hook`
signature `(env)` for 18+ carried to 19, etc.). **That migration is separate
work** and is NOT part of this structural plan. Just leave the directory in
place; do not modify it here.

> **Update (2026-09-04):** the view-syntax migration has since landed on
> `19.0` (`[MIG]` commits); the remaining Odoo-19 fixes (xpaths, search-view
> `<group>`, `read_group`→`_read_group`, version bump) are tracked in the
> supermodule `PLAN.md` and are being executed in the current pass.

---

## 8. Push the new `19.0` branch to origin

```bash
git push -u origin 19.0
```

Requires write access to `Mueve-TEC/odoo-argentina`. After push, confirm:

```bash
git ls-remote --heads origin 19.0     # should print the published SHA
```

> ⚠️ Before pushing, re-read Step 3.1 + the verification commands below. A
> push is the first hard-to-undo step. If anything in verification looked off,
> fix locally first.

---

## 9. Final verification

```bash
git rev-parse --abbrev-ref HEAD        # => 19.0
git log --oneline -16                  # see: [DOC] commit, 4× Merge/Squash pairs, [REF] drop, then 18.0 history
ls adhoc-modules                       # 4 dirs
ls scripts                             # pull-upstream.sh
ls mueve-modules                       # l10n_ar_inflation_adjustment (untouched, 18.0 code)
git remote -v                          # only origin (git@github.com:Mueve-TEC/odoo-argentina.git) — no stray remotes added
bash -n scripts/pull-upstream.sh       # OK
./scripts/pull-upstream.sh            # prints Usage, exit 1
grep -n "\[FIX-adhoc\]" README.md     # the workflow section is present
```

Optionally, confirm subtree metadata is intact for one prefix (should print
the upstream commit SHA the subtree tracks):

```bash
git subtree split --prefix=adhoc-modules/account-payment   # prints a SHA (not committed; safe)
```

---

## 10. Rollback (if needed)

**Before Step 8 push (`origin/19.0` does not exist yet):**
```bash
git checkout 18.0
git branch -D 19.0
```
Clean slate, nothing remote to clean.

**After Step 8 push:**
```bash
git push origin --delete 19.0     # if you really want to unpublish
git checkout 18.0
git branch -D 19.0
```
(Do not force-push to repair — just delete and re-run from Step 2.)

---

## 11. Summary for the executor to report back

When done, paste back:
- `git log --oneline` (top ~16 lines) on `19.0`.
- `ls adhoc-modules` output.
- The `git ls-remote --heads origin 19.0` line (proves it's published).
- Any upstream repo skipped (no `19.0` branch) — ideally none.

---

## Appendix — command quick-reference

| Action | Command |
|---|---|
| Add an upstream (done once, Step 3) | `git subtree add --prefix=adhoc-modules/<name> https://github.com/ingadhoc/<name>.git 19.0` |
| Update an upstream (repeatable) | `./scripts/pull-upstream.sh <name>` |
| Audit local upstream fixes | `git log --grep='^\[FIX-adhoc\]' --name-only -- adhoc-modules/` |
| Verify subtree metadata | `git subtree split --prefix=adhoc-modules/<name>` (prints SHA, no commit) |
| Inspect upstream behind a subtree | `git log --oneline adhoc-modules/<name> | head` (sees squash/import commits only) |

---

## Appendix — what we deliberately did NOT do

- **No forks of ingadhoc repos.** Local fixes stay in `odoo-argentina` history
  only; subtree pull re-merges them on top of new upstream via 3-way merge.
- **No git submodules for upstream.** Would require fork-backed reachable pins;
  rejected for this repo's workflow.
- **No changes to the supermodule** (`soltec-localdev-odoo19`). Bumping its
  `submodules/odoo-argentina` pointer to the new `19.0` branch and re-running
  `copy_addons.sh` is a separate, explicitly-skipped step.
- **No migration of `mueve-modules/*` to Odoo 19 here** — that is real Odoo
  migration work, flagged in Step 7, done separately.
- **No addition of OCA pristine repos** (`partner-contact`,
  `reporting-engine`). They remain declared in `oca_dependencies.txt` for
  whoever wants to materialize them via gitaggregate later (not vendored).
- **No persistent upstream git remotes added** (`git remote -v` keeps only
  `origin`). The helper script holds the upstream URLs, keeping the remote list
  clean.
