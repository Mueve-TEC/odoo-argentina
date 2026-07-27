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
