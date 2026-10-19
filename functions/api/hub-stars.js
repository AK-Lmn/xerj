// /api/hub-stars — hub-native stars for contributors and corpora on hub.xerj.org.
//
// A visitor of the Corpus Hub can star a contributor (/contributors/<login>.html)
// or a corpus (/corpus/<slug>.html). These are HUB stars: separate from, and never
// mixed with, the GitHub star counts the pages also show.
//
// Built like functions/api/field-report.js (main): R2 storage, per-IP-hash rate
// limit, daily write cap, no raw IP stored, fail-open when the bucket is absent.
//
// ─────────────────────────────── CONTRACT ───────────────────────────────
//   GET  /api/hub-stars?kind=contributor&id=<login>   → { ok, enabled, count, starred }
//   GET  /api/hub-stars?kind=corpus                   → { ok, enabled, counts: {id: n} }
//   POST /api/hub-stars  {"kind":"contributor"|"corpus","id":"..."}
//        200 { ok:true, enabled:true, count, starred:true, already? }
//   kind/id unknown → 400 · not JSON → 415 · >1 KB → 413 · cross-origin → 403
//   same source within RATE_WINDOW_MS → 429 · daily cap → 503
//   No HUB_STARS binding → GET { ok:true, enabled:false }, POST 503 enabled:false
//   (the pages hide the star control when enabled is false).
//   One star per source (ip hash) per target; there is no un-star.
//
// ─────────────────────── STORAGE: R2, free-tier-safe ────────────────────
// Binding HUB_STARS → bucket xerj-hub-stars (see wrangler.toml). Objects:
//   stars/<kind>/<id>          body + customMetadata.count = the count
//   who/<kind>/<id>/<ipHash>   marker: this source already starred it
//   rl/<ipHash>                last accepted star (ms); rate limit
//   meta/count-<YYYY-MM-DD>    accepted stars today; daily cap
// An accepted star = 4 Class-A writes; DAILY_CAP×4 = 8,000/day ≈ 240k/mo, far
// under R2's free 1M Class-A/mo. Rejected and duplicate stars write nothing.
// The listing GET (one Class-A list per page of 1000) is edge-cached for 60s.
// The count is read-modify-write: two stars on the same target in the same
// instant can lose one. Acceptable for a vanity counter; no money depends on it.
// Lifecycle rule worth adding on the bucket: expire rl/ and meta/ after 2 days.
//
// Valid targets come from the static file /contributors/stars-targets.json that
// tools/corpus-hub-site/gen.py writes on every deploy, so a star can only land on
// a page that exists.

const DAILY_CAP = 2000;
const RATE_WINDOW_MS = 5_000;   // one accepted star per source every 5s
const MAX_BODY = 1024;
const KINDS = ['contributor', 'corpus'];
const ID_RE = /^[a-z0-9][a-z0-9._-]{0,99}$/;
const TARGETS_PATH = '/contributors/stars-targets.json';
const ORIGIN_OK = /^https:\/\/((www\.)?hub\.xerj\.org|([a-z0-9-]+\.)?xerj-hub\.pages\.dev)$|^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/;

const JSON_HEADERS = { 'content-type': 'application/json', 'cache-control': 'no-store' };
const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { ...JSON_HEADERS, ...extra } });

async function sha256hex(input) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

let targetsCache = null;       // per isolate; refreshed on the next cold start / deploy
async function targets(env, request) {
  if (targetsCache) return targetsCache;
  try {
    const url = new URL(TARGETS_PATH, request.url);
    const res = env.ASSETS ? await env.ASSETS.fetch(url) : null;
    if (!res || !res.ok) return null;
    const t = await res.json();
    targetsCache = Object.fromEntries(KINDS.map((k) => [k, new Set((t[k] || []).map((x) => String(x).toLowerCase()))]));
    return targetsCache;
  } catch (_) { return null; }
}

async function readCount(bucket, kind, id) {
  try {
    const o = await bucket.get(`stars/${kind}/${id}`);
    return o ? (parseInt(await o.text(), 10) || 0) : 0;
  } catch (_) { return 0; }
}

async function sourceHash(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || '';
  return ip ? sha256hex(ip + (env.HUB_STARS_SALT || 'xerj-hub-stars-v1')) : 'noip';
}

export async function onRequest(context) {
  const method = context.request.method.toUpperCase();
  if (method === 'GET') return handleGet(context);
  if (method === 'POST') return handlePost(context);
  return json({ ok: false, error: 'method not allowed; use GET or POST' }, 405, { allow: 'GET, POST' });
}

async function handleGet({ request, env, waitUntil }) {
  const url = new URL(request.url);
  const kind = url.searchParams.get('kind') || '';
  const id = (url.searchParams.get('id') || '').toLowerCase();
  if (!KINDS.includes(kind)) return json({ ok: false, error: 'kind must be contributor or corpus' }, 400);
  if (id && !ID_RE.test(id)) return json({ ok: false, error: 'invalid id' }, 400);
  const bucket = env.HUB_STARS;
  if (!bucket) return json({ ok: true, enabled: false });

  if (id) {
    const ipHash = await sourceHash(request, env);
    let starred = false;
    try { starred = !!(await bucket.head(`who/${kind}/${id}/${ipHash}`)); } catch (_) { /* unknown → false */ }
    return json({ ok: true, enabled: true, count: await readCount(bucket, kind, id), starred });
  }

  // All counts for one kind (the wall). Edge-cached so a busy page costs one list.
  const cache = typeof caches !== 'undefined' ? caches.default : null;
  const cacheKey = new Request(`${url.origin}/api/hub-stars?kind=${kind}`, { method: 'GET' });
  if (cache) { const hit = await cache.match(cacheKey); if (hit) return hit; }
  const counts = {};
  try {
    let cursor;
    for (let page = 0; page < 20; page++) {
      const res = await bucket.list({ prefix: `stars/${kind}/`, cursor, include: ['customMetadata'] });
      for (const o of res.objects) {
        const n = parseInt((o.customMetadata || {}).count, 10);
        if (n > 0) counts[o.key.slice(`stars/${kind}/`.length)] = n;
      }
      if (!res.truncated) break;
      cursor = res.cursor;
    }
  } catch (e) {
    console.log('[hub-stars] list failed:', String(e));
    return json({ ok: false, enabled: true, error: 'storage unavailable' }, 503);
  }
  const resp = new Response(JSON.stringify({ ok: true, enabled: true, counts }), {
    headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=60' },
  });
  if (cache) { const p = cache.put(cacheKey, resp.clone()); if (waitUntil) waitUntil(p); else await p; }
  return resp;
}

async function handlePost({ request, env }) {
  const origin = request.headers.get('origin');
  if (origin && !ORIGIN_OK.test(origin)) return json({ ok: false, error: 'cross-origin stars are not accepted' }, 403);
  const ct = (request.headers.get('content-type') || '').toLowerCase();
  if (!ct.includes('application/json')) return json({ ok: false, error: 'content-type must be application/json' }, 415);
  const declared = parseInt(request.headers.get('content-length') || '0', 10);
  if (Number.isFinite(declared) && declared > MAX_BODY) return json({ ok: false, error: 'body too large' }, 413);
  let raw;
  try { raw = await request.text(); } catch (_) { return json({ ok: false, error: 'could not read body' }, 400); }
  if (raw.length > MAX_BODY) return json({ ok: false, error: 'body too large' }, 413);
  let body;
  try { body = JSON.parse(raw); } catch (_) { return json({ ok: false, error: 'invalid JSON body' }, 400); }
  if (!body || typeof body !== 'object' || Array.isArray(body)) return json({ ok: false, error: 'body must be a JSON object' }, 400);
  const kind = body.kind;
  const id = typeof body.id === 'string' ? body.id.toLowerCase() : '';
  if (!KINDS.includes(kind) || !ID_RE.test(id)) return json({ ok: false, error: 'kind must be contributor or corpus, with a valid id' }, 400);

  const bucket = env.HUB_STARS;
  if (!bucket) return json({ ok: false, enabled: false, error: 'hub stars are not enabled yet' }, 503);

  const t = await targets(env, request);
  if (!t) return json({ ok: false, enabled: true, error: 'star targets unavailable' }, 503);
  if (!t[kind].has(id)) return json({ ok: false, error: `unknown ${kind}` }, 400);

  const ipHash = await sourceHash(request, env);
  const whoKey = `who/${kind}/${id}/${ipHash}`;
  try {
    if (await bucket.head(whoKey))   // already starred by this source: no writes
      return json({ ok: true, enabled: true, count: await readCount(bucket, kind, id), starred: true, already: true });
  } catch (_) { /* fall through; the rate limit still bounds writes */ }

  const rlKey = `rl/${ipHash}`;
  try {
    const prev = await bucket.get(rlKey);
    if (prev && Date.now() - (parseInt(await prev.text(), 10) || 0) < RATE_WINDOW_MS)
      return json({ ok: false, error: 'rate limited: one star every few seconds' }, 429);
  } catch (_) { /* fail open; the daily cap still bounds writes */ }

  const today = new Date().toISOString().slice(0, 10);
  const cntKey = `meta/count-${today}`;
  let today_n = 0;
  try { const c = await bucket.get(cntKey); if (c) today_n = parseInt(await c.text(), 10) || 0; } catch (_) { today_n = 0; }
  if (today_n >= DAILY_CAP) return json({ ok: false, error: 'daily star capacity reached; try again tomorrow' }, 503);

  const count = (await readCount(bucket, kind, id)) + 1;
  try {
    await bucket.put(rlKey, String(Date.now()));
    await bucket.put(whoKey, '1');
    await bucket.put(`stars/${kind}/${id}`, String(count), { customMetadata: { count: String(count) } });
    await bucket.put(cntKey, String(today_n + 1));
  } catch (e) {
    console.log('[hub-stars] R2 write failed:', String(e));
    return json({ ok: false, enabled: true, error: 'storage unavailable' }, 503);
  }
  return json({ ok: true, enabled: true, count, starred: true });
}
