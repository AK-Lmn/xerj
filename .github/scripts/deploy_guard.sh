#!/usr/bin/env bash
# deploy_guard.sh — stop a Pages deploy that cannot serve /api/field-report.
#
#   deploy_guard.sh lint        committed wrangler.toml has no stand-in KV id,
#                               and every functions/**/*.js route is listed in
#                               landing/_routes.json (default)
#   deploy_guard.sh self-test   the lint fails on a planted stand-in id and on
#                               a function whose route was left out
#   deploy_guard.sh smoke       non-writing probes of a deployed site:
#                               OPTIONS → 204, GET → 405, POST text/plain → 415,
#                               and the field-report schema JSON parses.
#                               SITE defaults to https://xerj.org. No JSON body
#                               is posted, so nothing is stored.
#
# Exit 0 when the check holds. Exit 1 with a ::error:: line when it does not.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${1:-lint}"

# A Workers KV namespace id is 32 hex characters. Anything else in that slot
# (including the stand-in that broke the #1760 deploy) is not bindable.
KV_ID_RE='^[0-9a-fA-F]{32}$'

die() {
  echo "::error::$*" >&2
  exit 1
}

# Lint wrangler.toml at $1 and _routes.json at $2 against functions under $3.
# Returns 1 on a violation. Does not exit the process (self-test depends on that).
lint_tree() {
  local wrangler="$1" routes="$2" functions="$3" failed=0
  [ -f "$wrangler" ] || { echo "::error::missing $wrangler" >&2; return 1; }
  [ -f "$routes" ] || { echo "::error::missing $routes" >&2; return 1; }
  [ -d "$functions" ] || { echo "::error::missing $functions" >&2; return 1; }

  if grep -n 'REPLACE_WITH' "$wrangler" >&2; then
    echo "::error::$wrangler contains a REPLACE_WITH stand-in id. Remove it. The deploy script injects a real FIELD_REPORTS id, or deploys with the binding omitted." >&2
    return 1
  fi

  # Every id = "..." under [[kv_namespaces]] must be a real namespace id.
  python3 - "$wrangler" "$KV_ID_RE" <<'PY'
import re, sys
path, id_re = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
blocks = re.split(r"(?m)^\[\[", text)
bad = []
for block in blocks:
    if not block.startswith("kv_namespaces]]"):
        continue
    ids = re.findall(r'(?m)^\s*id\s*=\s*"([^"]*)"', block)
    if not ids:
        bad.append("[[kv_namespaces]] block has no id")
        continue
    for value in ids:
        if not re.fullmatch(id_re, value):
            bad.append(f"kv namespace id {value!r} is not 32 hex characters")
if bad:
    sys.stderr.write("\n".join(bad) + "\n")
    sys.exit(1)
PY
  failed=$?
  [ "$failed" -eq 0 ] || return 1

  # Pages maps functions/<path>.js to /<path>, dropping only the .js suffix
  # (functions/get.ps1.js → /get.ps1, functions/api/field-report.js → /api/field-report).
  python3 - "$routes" "$functions" <<'PY'
import json, sys
from pathlib import Path
routes_path, functions = Path(sys.argv[1]), Path(sys.argv[2])
doc = json.loads(routes_path.read_text(encoding="utf-8"))
include = set(doc.get("include") or [])
missing = []
for js in sorted(functions.rglob("*.js")):
    rel = js.relative_to(functions).as_posix()
    if not rel.endswith(".js"):
        continue
    url = "/" + rel[: -len(".js")]
    if url not in include:
        missing.append(f"{rel} serves {url}, which is not in {routes_path} include")
if missing:
    sys.stderr.write("\n".join(missing) + "\n")
    sys.exit(1)
print(f"routes: {len(list(functions.rglob('*.js')))} function file(s) listed in {routes_path}")
PY
}

lint() {
  lint_tree "$ROOT/wrangler.toml" "$ROOT/landing/_routes.json" "$ROOT/functions" \
    || die "deploy guard failed"
  echo "lint: wrangler.toml has no stand-in KV id"
}

self_test() {
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  mkdir -p "$tmp/functions/api" "$tmp/landing"

  # A clean tree passes.
  cat > "$tmp/wrangler.toml" <<'EOF'
name = "xerj"
[[r2_buckets]]
binding = "LEADS"
bucket_name = "xerj-leads"
EOF
  printf '%s\n' 'export function onRequest(){ return new Response("ok"); }' > "$tmp/functions/api/field-report.js"
  printf '%s\n' '{"version":1,"include":["/api/field-report"],"exclude":[]}' > "$tmp/landing/_routes.json"
  # _routes path in the helper is the second arg; functions is the third.
  # The clean fixture uses landing/_routes.json only as a file path.
  lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions"

  # A stand-in id must fail.
  cat > "$tmp/wrangler.toml" <<'EOF'
[[kv_namespaces]]
binding = "FIELD_REPORTS"
id = "REPLACE_WITH_FIELD_REPORTS_KV_NAMESPACE_ID"
EOF
  if lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions" 2>"$tmp/err"; then
    die "self-test: a REPLACE_WITH id was accepted"
  fi
  grep -q 'REPLACE_WITH' "$tmp/err" || die "self-test: failure did not name the stand-in id"

  # A non-hex id must fail even without the stand-in word.
  cat > "$tmp/wrangler.toml" <<'EOF'
[[kv_namespaces]]
binding = "FIELD_REPORTS"
id = "not-a-real-namespace"
EOF
  if lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions" 2>"$tmp/err"; then
    die "self-test: a non-hex KV id was accepted"
  fi

  # A real-shaped id is allowed (the owner may commit one later).
  cat > "$tmp/wrangler.toml" <<'EOF'
[[kv_namespaces]]
binding = "FIELD_REPORTS"
id = "0123456789abcdef0123456789abcdef"
EOF
  lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions"

  # #1769 commented the block out, including a prose placeholder. Comments
  # must not fail the guard; only an active [[kv_namespaces]] id does.
  cat > "$tmp/wrangler.toml" <<'EOF'
# [[kv_namespaces]]
# binding = "FIELD_REPORTS"
# id = "<the id it printed>"
name = "xerj"
EOF
  lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions"

  # A function that is not routed must fail.
  printf '%s\n' 'export function onRequest(){}' > "$tmp/functions/lead.js"
  if lint_tree "$tmp/wrangler.toml" "$tmp/landing/_routes.json" "$tmp/functions" 2>"$tmp/err"; then
    die "self-test: an unrouted function was accepted"
  fi
  grep -q '/lead' "$tmp/err" || die "self-test: failure did not name /lead"

  echo "self-test: stand-in ids and unrouted functions are rejected"
}

smoke_once() {
  local site="$1" path code body
  path="${site%/}/api/field-report"

  code="$(curl -sS -o /dev/null -w '%{http_code}' -X OPTIONS "$path" \
    -H 'Origin: https://example.invalid' -H 'Access-Control-Request-Method: POST')" \
    || { echo "OPTIONS $path failed to connect" >&2; return 1; }
  [ "$code" = "204" ] || { echo "OPTIONS $path returned $code, expected 204" >&2; return 1; }

  code="$(curl -sS -o /dev/null -w '%{http_code}' -X GET "$path")" \
    || { echo "GET $path failed to connect" >&2; return 1; }
  [ "$code" = "405" ] || { echo "GET $path returned $code, expected 405 (the function is not deployed if this is 404)" >&2; return 1; }

  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$path" \
    -H 'Content-Type: text/plain' --data 'not json')" \
    || { echo "POST $path failed to connect" >&2; return 1; }
  [ "$code" = "415" ] || { echo "POST text/plain $path returned $code, expected 415" >&2; return 1; }

  body="$(curl -fsS "${site%/}/docs/agents/schemas/field-report.json")" \
    || { echo "field-report schema did not return 200" >&2; return 1; }
  python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["required"]==["agent","used_for","verdict"], d' "$body" \
    || { echo "field-report schema JSON did not parse or is missing required fields" >&2; return 1; }

  echo "smoke: OPTIONS 204, GET 405, POST text/plain 415, schema JSON ok ($site)"
}

smoke() {
  local site="${SITE:-https://xerj.org}" attempt
  # Pages can take a few seconds to serve a deployment that just finished.
  # These probes write nothing: no application/json body is sent.
  for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if smoke_once "$site"; then
      return 0
    fi
    echo "smoke: attempt $attempt failed; retrying in 10s" >&2
    sleep 10
  done
  die "smoke: $site/api/field-report did not meet the contract"
}

case "$MODE" in
  lint) lint ;;
  self-test) self_test ;;
  smoke) smoke ;;
  *) die "usage: $(basename "$0") lint|self-test|smoke" ;;
esac
