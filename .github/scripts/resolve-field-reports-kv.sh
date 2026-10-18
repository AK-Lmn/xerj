#!/usr/bin/env bash
# resolve-field-reports-kv.sh — inject the FIELD_REPORTS KV binding, or leave
# it off so `wrangler pages deploy` still succeeds.
#
# The committed wrangler.toml has no namespace id (a stand-in id fails the
# deploy, which is what happened to #1760). This script edits the checkout
# copy only. It never commits.
#
# Resolution order:
#   1. FIELD_REPORTS_KV_NAMESPACE_ID (GitHub secret the owner sets)
#   2. `wrangler kv namespace list`, title == FIELD_REPORTS
#   3. `wrangler kv namespace create FIELD_REPORTS` when the token allows it
#
# Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID for 2 and 3. The Pages
# token in this repo is documented as "Cloudflare Pages:Edit". If that token
# cannot read or create KV, this script warns and deploys without the binding.
# The function then accepts reports and does not store them.
#
# The owner must set FIELD_REPORTS_KV_NAMESPACE_ID (32 hex chars) — or grant
# the token Workers KV edit — before reports are stored.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

WRANGLER_TOML="${WRANGLER_TOML:-$ROOT/wrangler.toml}"
TITLE="FIELD_REPORTS"
ID_RE='^[0-9a-fA-F]{32}$'

warn() { echo "::warning::$*" >&2; }

inject() {
  local id="$1"
  python3 - "$WRANGLER_TOML" "$id" <<'PY'
import re, sys
from pathlib import Path
path, ns_id = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
text = re.sub(
    r"\n*\[\[kv_namespaces\]\]\n(?:.*\n)*?binding = \"FIELD_REPORTS\"\n(?:.*\n)*?id = \"[^\"]*\"\n?",
    "\n",
    text,
)
text = text.rstrip() + (
    "\n\n[[kv_namespaces]]\n"
    "binding = \"FIELD_REPORTS\"\n"
    f"id = \"{ns_id}\"\n"
)
path.write_text(text, encoding="utf-8")
PY
  echo "FIELD_REPORTS binding injected for this deploy (id ${id:0:8}…)."
  echo "The id is not committed. Set the GitHub secret FIELD_REPORTS_KV_NAMESPACE_ID so the next deploy does not depend on a lookup."
}

list_id() {
  local raw
  raw="$(npx --yes wrangler@3 kv namespace list 2>&1)" || return 1
  printf '%s' "$raw" | python3 -c '
import json, sys
raw = sys.stdin.read()
start, end = raw.find("["), raw.rfind("]")
if start < 0 or end < start:
    sys.exit(1)
try:
    data = json.loads(raw[start:end + 1])
except json.JSONDecodeError:
    sys.exit(1)
for ns in data:
    if isinstance(ns, dict) and ns.get("title") == "FIELD_REPORTS" and ns.get("id"):
        print(ns["id"])
        sys.exit(0)
sys.exit(1)
'
}

create_id() {
  local raw
  raw="$(npx --yes wrangler@3 kv namespace create "$TITLE" 2>&1)" || true
  printf '%s\n' "$raw" >&2
  printf '%s' "$raw" | sed -n 's/.*id = "\([0-9a-fA-F]\{32\}\)".*/\1/p' | head -n 1
}

if [ -n "${FIELD_REPORTS_KV_NAMESPACE_ID:-}" ]; then
  if [[ "$FIELD_REPORTS_KV_NAMESPACE_ID" =~ $ID_RE ]]; then
    inject "$FIELD_REPORTS_KV_NAMESPACE_ID"
    exit 0
  fi
  warn "FIELD_REPORTS_KV_NAMESPACE_ID is set but is not 32 hex characters. Ignoring it."
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  warn "No Cloudflare token for a KV lookup, and no usable FIELD_REPORTS_KV_NAMESPACE_ID. Deploying without the KV binding. The owner must set that secret to the 32-hex namespace id (or grant Workers KV edit) before /api/field-report stores reports."
  exit 0
fi

id=""
if id="$(list_id)"; then
  if [[ "$id" =~ $ID_RE ]]; then
    echo "Found existing KV namespace titled $TITLE."
    inject "$id"
    exit 0
  fi
fi

id="$(create_id || true)"
if [[ "${id:-}" =~ $ID_RE ]]; then
  echo "Created KV namespace titled $TITLE."
  inject "$id"
  exit 0
fi

# Create can fail because the namespace already exists and list returned
# nothing parseable. One more list, then give up without failing the deploy.
if id="$(list_id)"; then
  if [[ "$id" =~ $ID_RE ]]; then
    inject "$id"
    exit 0
  fi
fi

warn "Could not look up or create the FIELD_REPORTS KV namespace with the existing Cloudflare token (it may only have Pages edit). Deploying WITHOUT the KV binding so the site still ships. /api/field-report will accept reports and not store them. The owner must create the namespace and set the GitHub secret FIELD_REPORTS_KV_NAMESPACE_ID."
exit 0
