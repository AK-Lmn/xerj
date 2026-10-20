# Corpus Hub v2 — signed-catalogue deploy runbook (hub.xerj.org)

**What this is:** the verified, one-pass procedure to publish the first signed
`catalogue.json` to `https://hub.xerj.org/api/v1/catalogue.json`, plus the
pre-flight gates, rollback, and the proof that a normal `landing/` deploy cannot
wipe it. Written off `corpus-hub` (`git worktree` at HEAD `a5bbacd3f`). This file
is operational notes, not a claim that the deploy has run — it has **not**.

**Last verified:** 2026-10-19, against `corpus-hub` and the live
`repos/xerj-org/xerj` GitHub config (read-only). **Source of truth on conflict:**
the workflow files themselves — `.github/workflows/hub-packs.yml` and
`.github/workflows/deploy-hub-pages.yml` — win over this prose.

---

## 0. TL;DR — the deploy, once the blocker below clears

```sh
# (one-time) opt in to serving the catalogue — same switch both workflows read
gh variable set HUB_CATALOGUE_DEPLOY --repo xerj-org/xerj --body true

# first publish: first_catalogue=true (the live URL still serves HTML, not a 404);
# max_builds=0 so this run only rebuilds + deploys the catalogue from the packs
# already published — it does NOT spend 90 min rebuilding corpus packs.
gh workflow run hub-packs.yml --repo xerj-org/xerj --ref corpus-hub \
  -f first_catalogue=true -f max_builds=0

# verify (full checklist in §4): expect HTTP 200 and a body starting with '{', not '<'
curl -s -o /tmp/live.json -w '%{http_code}\n' https://hub.xerj.org/api/v1/catalogue.json && head -c1 /tmp/live.json
```

Do **not** run this until §3 (pre-flight) passes, in particular the size gate.

> ⛔ **BLOCKER AS OF 2026-10-19 — the catalogue is over 2 MiB on `corpus-hub`.**
> The term-sketch sizing fix (16 bits/term + 1500-term cap; 1.70 MB / 1.04 MB
> gzip is the `catalogue.json` size reported on #1737's branch at `d5f89be27`,
> a projection for `corpus-hub`, not a measurement of code in this tree) is
> **not on `corpus-hub`**. Its known
> PR **#1737** ("perf(hub): size and route the catalogue at full (512-corpus)
> scale", commit `d5f89be27`) is **CLOSED, not merged**, and targets `main`, not
> `corpus-hub`. On `corpus-hub` today `engine/crates/xerj-hub/src/sketch.rs` sizes
> each sketch at `8·max(1024, 10·distinct)` bits with **no cap on terms**
> (`build_catalogue.rs` pushes every symbol raw+lowercase, every path component,
> every topic word), so 175 corpora extrapolate well past the 2 MiB budget.
> `check-catalogue` (`hub_packs.py:572`, `>= 2*1024*1024`) will **fail the run**
> and nothing will deploy. **Confirm a < 2 MiB catalogue has actually landed on
> `corpus-hub` (dry run in §3.1) before triggering.** The task brief says to
> assume this fix lands; this runbook is written for that state but will not let
> you deploy an oversized catalogue.

---

## 1. Current state (verified read-only)

| Fact | Value | Source |
|---|---|---|
| `HUB_SIGNING_SEED` secret | **present** (updated 2026-10-14) | `gh api .../actions/secrets/HUB_SIGNING_SEED` |
| `HUB_CATALOGUE_DEPLOY` variable | **unset** (no repo variables exist) | `gh api .../actions/variables` → empty |
| Compiled `HUB_PUBKEY_HEX` (corpus-hub) | `b68899321ec01ad8d0130d6e4790d9c75ffbc03bb0271f0a1522114c43562936` | `engine/crates/xerj-common/src/hub.rs:48` |
| Live `…/api/v1/catalogue.json` | HTML page, HTTP 200 (no catalogue yet) | task brief + guard design |
| Backfill coverage | **175 of 232** corpora published at latest attempt | `benchmarks/hub-backfill/REPORT.md` |
| Size fix on corpus-hub | **NO** (PR #1737 closed unmerged; sketch uncapped) | git / `gh pr view 1737` |

Because the variable is unset, **no catalogue is being deployed today**, which is
why the URL serves HTML. That is the expected pre-opt-in state.

---

## 2. How the catalogue is built, signed, gated, and where it lands

Two Cloudflare Pages projects, and they are the crux of the "won't wipe" proof:

| Pages project | Serves | Deployed by | Trigger |
|---|---|---|---|
| **`xerj`** | `xerj.org` (the `landing/` site) | `deploy-pages.yml` → `pages deploy landing --project-name=xerj` | push to **main** on `landing/**` |
| **`xerj-hub`** | `hub.xerj.org` (the registry site **+** `api/v1/catalogue.json`) | `hub-packs.yml` (catalogue job) **and** `deploy-hub-pages.yml` → `wrangler pages deploy tools/corpus-hub-site/out --project-name=xerj-hub` | push to **corpus-hub** / dispatch |

They are **different projects**. A `landing/` deploy targets `xerj` and can never
touch `xerj-hub`'s `api/v1/catalogue.json`. (See §5.)

**Build + sign (hub-packs.yml → `catalogue` job, needs preflight/plan/build-xerj/pack):**

1. `preflight` proves `HUB_SIGNING_SEED` derives to the compiled `HUB_PUBKEY_HEX`
   (refuses to publish packs no client can verify) and that the run is on
   `corpus-hub` (or `dry_run`).
2. Downloads the current pin's pack of **every** live corpus from GitHub Releases
   (any missing pack aborts — a catalogue is a complete snapshot).
3. `bin/xerj hub build-catalogue --registry tools/xerj-code/hub --backlog
   tools/xerj-code/hub/backlog/backlog-100.json --packs <dir> --tags <tsv>
   --out catalogue.json --sign-key <seed>` → writes `catalogue.json` +
   `catalogue.json.sig` (hub-packs.yml:716-731).
4. **Check the catalogue** (hub-packs.yml:736-797): `ed25519.sh verify` under the
   compiled pubkey, then `hub_packs.py check-catalogue` (size < 2 MiB,
   `format_version==1`, every pin == manifest pin, every `pack_url` is that pin's
   release asset, `sig_url == pack_url+".sig"`, `pack_sha256` 64-hex,
   `pack_bytes` > 0, and — against the live catalogue — no live corpus dropped).
   Any violation → exit 1 → the job fails → **nothing deploys**.
5. Uploads the `catalogue` artifact (14-day retention) **always** (even on a dry
   run / when not deploying) — this is what the pre-flight downloads.
6. **Deploy** (hub-packs.yml:810-825) only when
   `!dry_run && vars.HUB_CATALOGUE_DEPLOY=='true' && packs exist`: regenerates
   the site, copies the catalogue to `out/api/v1/`, and
   `wrangler pages deploy … --project-name=xerj-hub`.

**first_catalogue** (hub-packs.yml:761-795): the delisting guard compares against
the **live** catalogue. A clean 404 = "none yet, first publish". The live URL
today answers **200 with HTML**, which reads as *absent-but-not-404*; when the run
is deploying, that is **fatal unless `first_catalogue=true`** (which excuses only a
missing/HTML catalogue, never an unreadable-but-present one). So the **first**
real deploy needs `first_catalogue=true`; later deploys do not.

---

## 3. Pre-flight checklist (all must pass before §4)

### 3.1 Dry run — the real size + signature measurement (no deploy)

```sh
gh workflow run hub-packs.yml --repo xerj-org/xerj --ref corpus-hub \
  -f dry_run=true -f max_builds=0
# then watch it:
gh run watch "$(gh run list --repo xerj-org/xerj --workflow hub-packs.yml -L1 --json databaseId --jq '.[0].databaseId')"
```

A dry run builds, signs, and runs **Check the catalogue** (size + signature +
pins) against the **real** packs and key, and uploads the `catalogue` artifact,
but deploys nothing (`DEPLOYING` is false, so the HTML live URL is only a
warning). Inspect it:

```sh
RID=$(gh run list --repo xerj-org/xerj --workflow hub-packs.yml -L1 --json databaseId --jq '.[0].databaseId')
gh run download "$RID" --repo xerj-org/xerj --name catalogue --dir /tmp/cat
wc -c /tmp/cat/catalogue.json                                  # [ ] GATE: < 2097152 bytes
bash tools/hub-packs/ed25519.sh verify \
  b68899321ec01ad8d0130d6e4790d9c75ffbc03bb0271f0a1522114c43562936 \
  /tmp/cat/catalogue.json /tmp/cat/catalogue.json.sig          # [ ] GATE: exit 0
jq '.format_version, (.corpora|length)' /tmp/cat/catalogue.json # [ ] 1, and ~175
```

- [ ] **Size < 2 MiB.** The run's "Check the catalogue" step also prints
      `check-catalogue: N corpora, M bytes`. If it instead errors with "over the
      2097152-byte budget", **STOP — the size fix (§0 blocker) is not on
      corpus-hub.**
- [ ] **Signature verifies** under the compiled pubkey (above, and in the run).
- [ ] **Coverage.** `N` corpora should be in the expected range (current backfill
      is **175/232 ≈ 75 %**). A large shortfall (e.g. << 150) means packs went
      missing — investigate `benchmarks/hub-backfill/REPORT.md` before publishing;
      a thin first catalogue is hard to walk back once clients cache it.

### 3.2 Secrets / key / variable

- [ ] `HUB_SIGNING_SEED` present (verified: yes) — the dry run also re-proves it
      matches the compiled pubkey in `preflight`.
- [ ] Compiled `HUB_PUBKEY_HEX` == `b68899…62936` (verified: yes).
- [ ] `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` secrets present (the
      `xerj-hub` project deploy uses them; same pair as the landing deploy).
- [ ] You are about to set `HUB_CATALOGUE_DEPLOY=true` and understand the
      invariant in §6 (**never unset it once the catalogue is live**).

### 3.3 Only one catalogue publish in flight

- [ ] No other `hub-packs.yml` run is mid-publish (`concurrency: hub-packs-publish`
      serialises publishes, but don't dispatch a second on top of a running one).

---

## 4. The deploy (first publish)

```sh
# 1. opt in (one time). This is the ONLY switch both workflows read.
gh variable set HUB_CATALOGUE_DEPLOY --repo xerj-org/xerj --body true

# 2. publish the signed catalogue (first time → first_catalogue=true).
gh workflow run hub-packs.yml --repo xerj-org/xerj --ref corpus-hub \
  -f first_catalogue=true -f max_builds=0

# 3. watch; the catalogue job must reach "Deploy to Cloudflare Pages" green.
gh run watch "$(gh run list --repo xerj-org/xerj --workflow hub-packs.yml -L1 --json databaseId --jq '.[0].databaseId')"
```

**Inputs that matter:** `first_catalogue=true` (first publish only, because the
live URL serves HTML), `max_builds=0` (rebuild+deploy the catalogue from the
already-published packs; skip the long pack-build matrix — `plan` schedules 0, the
`pack` job is skipped on `count != '0'`, and the `catalogue` job still runs on
`!cancelled()`). Leave `dry_run` false. Everything else can stay default.

### Post-deploy verification

```sh
curl -fsS https://hub.xerj.org/api/v1/catalogue.json  -o /tmp/live.json
curl -fsS https://hub.xerj.org/api/v1/catalogue.json.sig -o /tmp/live.json.sig
head -c1 /tmp/live.json                                   # [ ] "{"  (JSON, not "<")
bash tools/hub-packs/ed25519.sh verify \
  b68899321ec01ad8d0130d6e4790d9c75ffbc03bb0271f0a1522114c43562936 \
  /tmp/live.json /tmp/live.json.sig                       # [ ] exit 0
jq '.format_version, (.corpora|length)' /tmp/live.json    # [ ] 1, ~175
# end-to-end from a client (routes a question through the live catalogue):
xerj hub pull lz4   # or any known corpus — must not say "catalogue unavailable"
```

CF Pages serves the real static file at that path; the HTML-200 only ever appears
for paths that have **no** file, so once the file is deployed the client gets JSON.

---

## 5. A normal `landing/` deploy cannot wipe the catalogue — verified

Three independent reasons, strongest first:

1. **Different Cloudflare project.** `landing/` deploys via `deploy-pages.yml`
   with `--project-name=xerj` (xerj.org). The catalogue lives in the
   **`xerj-hub`** project (hub.xerj.org), deployed only by `hub-packs.yml` and
   `deploy-hub-pages.yml` with `--project-name=xerj-hub`. A main→`landing/` push
   physically cannot write to `xerj-hub`.

2. **The hub-site deploy carries the catalogue forward (guard #1521).**
   `deploy-hub-pages.yml` is the one that *could* overwrite the whole `xerj-hub`
   site on an unrelated `corpus-hub` push (it triggers on `tools/xerj-code/hub/**`,
   `tools/packs/**`, `tools/corpus-hub-site/**`). Its **"Carry the signed catalogue
   into the site"** step (lines 46-85), gated on `HUB_CATALOGUE_DEPLOY=='true'`,
   re-fetches the newest `corpus-hub` `catalogue` artifact (verified under the
   compiled key), else the **live** catalogue, and copies it back into
   `out/api/v1/` before deploying. If it can find **neither** a usable artifact nor
   a verifiable live copy, it **`exit 1` and does not deploy** (fail-safe) rather
   than ship a site without the catalogue. So while the variable is `true`,
   `deploy-hub-pages.yml` either deploys **with** the catalogue or not at all.

3. **hub-packs.yml always rebuilds + carries its own fresh catalogue** and only
   deploys when `HUB_CATALOGUE_DEPLOY=='true'`; it never ships the site without it.

### Guards verified present on `corpus-hub`

| PR | What it guards | Where | Verified |
|---|---|---|---|
| **#1521** | a hub-site deploy can't delete `catalogue.json` (carries it forward, else fails) | `deploy-hub-pages.yml:46-85` | ✅ |
| **#1582** | the delisting guard can't be switched off by a "previous" that isn't a catalogue | `hub_packs.py:613-625` | ✅ |
| **#1587** | **client** refuses an HTML-200 body *before* the signature and *before* caching → "the hub catalogue is unavailable"; keeps the cached copy | `catalogue.rs:492` (`starts_like_json_object`) | ✅ |
| **#1588** | CI delisting guard reads the live catalogue **only if it is one**; HTML-200 = absent, fatal when deploying unless `first_catalogue` | `hub_packs.yml:761-795` | ✅ |

The client HTML-200 drop-guard is real: `fetch_and_store` (`catalogue.rs:492`)
bails on any body whose first non-whitespace byte isn't `{`, so a live HTML page
never reaches the signature step or the cache, and `load_catalogue` falls back to
the last good cached copy. A live HTML-200 therefore cannot silently disable the
guard.

---

## 6. Operational invariant — the one real sharp edge

> **Once the catalogue is live, NEVER unset / delete `HUB_CATALOGUE_DEPLOY`.**

The wipe protection in §5.2 is conditioned on `HUB_CATALOGUE_DEPLOY=='true'`. If
the variable is removed or set to anything else **after** a catalogue is live, the
next `deploy-hub-pages.yml` run (any `corpus-hub` push touching its watched paths,
or a manual dispatch) **skips the carry step and deploys a site without
`api/v1/catalogue.json` — wiping it.** Clients then see HTML-200 → "catalogue
unavailable" and fall back to their cache until the next good deploy. This is the
historical wipe risk (brief risk "a"); it is guarded *as long as the variable
stays `true`*. Treat the variable as permanent once set.

(Minor, non-wiping: `hub-packs.yml`'s catalogue deploy and `deploy-hub-pages.yml`
share no concurrency group, so a `corpus-hub` push that triggers both can race on
`xerj-hub`. Both carry a catalogue, so the worst case is a brief older-but-present
catalogue that self-heals on the next catalogue build — never a wipe. A follow-up
PR could add a shared `concurrency: xerj-hub-pages` group; it is **not** a blocker
and is intentionally **not** changed here, to keep the deploy path stable.)

---

## 7. Rollback

**Preferred — Cloudflare Pages dashboard (instant, no code):** in the `xerj-hub`
project, "Rollback to this deployment" on the previous good deployment (either the
prior signed catalogue, or the HTML-only site from before the first publish).
Clients tolerate a reverted-to-HTML path (guard #1587: "unavailable" → cached
copy), so a rollback does not break `xerj hub` for anyone with a cache.

**Re-publish a known-good catalogue:** re-dispatch §4 (with `first_catalogue=true`
if the live URL is back to HTML). The delisting guard will refuse to drop any
corpus that is still live.

**Do NOT roll back by unsetting `HUB_CATALOGUE_DEPLOY`** — per §6 that is itself
the wipe trigger on the next hub-site deploy.

---

## 8. Blockers & dependencies — summary for the human

1. ⛔ **Catalogue size (§0).** The < 2 MiB sketch-sizing fix is **not on
   corpus-hub**; PR **#1737** (its known carrier) is **closed, unmerged**, based on
   `main`. The deploy will fail at `check-catalogue` until a < 2 MiB catalogue
   lands on `corpus-hub`. **Confirm with the size owner / via the §3.1 dry run
   before triggering.** This runbook otherwise assumes it has landed (per the
   brief).
2. One-time: create repo variable `HUB_CATALOGUE_DEPLOY=true` (currently absent).
3. First dispatch must pass `first_catalogue=true` (live URL serves HTML, not 404).
4. Keep the variable `true` forever after go-live (§6).

**No deploy-path code bug was found that is unguarded:** the wipe risk is guarded
(#1521), the HTML-200 client drop-guard is guarded (#1587), the CI delisting guard
is guarded (#1582/#1588), and the 2 MiB gate is enforced (`hub_packs.py:572`). The
only true blocker is the catalogue size, which is owned elsewhere. Nothing in the
deploy path is changed by this PR.
