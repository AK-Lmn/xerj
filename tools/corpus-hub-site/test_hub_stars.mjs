// node --test tools/corpus-hub-site/test_hub_stars.mjs  (Node 18+; no dependencies)
// Exercises /api/hub-stars against an in-memory stand-in for the R2 binding.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { onRequest, sourceKey } from '../../functions/api/hub-stars.js';

function r2() {
  const m = new Map();
  const obj = (k) => ({ key: k, text: async () => m.get(k).body, customMetadata: m.get(k).meta });
  return {
    m, writes: 0,
    async get(k) { return m.has(k) ? obj(k) : null; },
    async head(k) { return m.has(k) ? obj(k) : null; },
    async put(k, body, o = {}) { this.writes++; m.set(k, { body: String(body), meta: o.customMetadata || {} }); },
    async list({ prefix }) { return { objects: [...m.keys()].filter((k) => k.startsWith(prefix)).map(obj), truncated: false }; },
  };
}
const ASSETS = { fetch: async () => new Response(JSON.stringify({ contributor: ['ann'], corpus: ['aider'] })) };
const ctx = (method, { body, query = '', ip = '1.2.3.4', origin, env }) => ({
  env,
  request: new Request(`https://hub.xerj.org/api/hub-stars${query}`, {
    method,
    headers: { 'content-type': 'application/json', 'CF-Connecting-IP': ip, ...(origin ? { origin } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  }),
});
const call = async (...a) => { const r = await onRequest(ctx(...a)); return [r.status, await r.json()]; };

test('no binding: GET says disabled, POST refuses, nothing faked', async () => {
  assert.deepEqual(await call('GET', { query: '?kind=contributor&id=ann', env: {} }), [200, { ok: true, enabled: false }]);
  const [s, b] = await call('POST', { body: { kind: 'contributor', id: 'ann' }, env: {} });
  assert.equal(s, 503); assert.equal(b.enabled, false);
});

test('star, duplicate, rate limit, listing', async () => {
  const env = { HUB_STARS: r2(), ASSETS };
  let [s, b] = await call('POST', { body: { kind: 'contributor', id: 'Ann' }, env });
  assert.equal(s, 200); assert.equal(b.count, 1);
  const w = env.HUB_STARS.writes;
  [s, b] = await call('POST', { body: { kind: 'contributor', id: 'ann' }, env });
  assert.equal(b.already, true); assert.equal(b.count, 1); assert.equal(env.HUB_STARS.writes, w, 'duplicate writes nothing');
  [s, b] = await call('POST', { body: { kind: 'corpus', id: 'aider' }, env });
  assert.equal(s, 429, 'same source inside the window');
  [s, b] = await call('POST', { body: { kind: 'corpus', id: 'aider' }, ip: '5.6.7.8', env });
  assert.equal(b.count, 1);
  [s, b] = await call('GET', { query: '?kind=contributor&id=ann', env });
  assert.deepEqual(b, { ok: true, enabled: true, count: 1, starred: true });
  [s, b] = await call('GET', { query: '?kind=contributor&id=ann', ip: '9.9.9.9', env });
  assert.equal(b.starred, false);
  [s, b] = await call('GET', { query: '?kind=contributor', env });
  assert.deepEqual(b.counts, { ann: 1 });
  assert.ok(![...env.HUB_STARS.m.keys()].some((k) => k.includes('1.2.3.4')), 'raw IP never stored');
});

test('rejects unknown targets, bad kinds, cross-origin', async () => {
  const env = { HUB_STARS: r2(), ASSETS };
  assert.equal((await call('POST', { body: { kind: 'contributor', id: 'nobody' }, env }))[0], 400);
  assert.equal((await call('POST', { body: { kind: 'user', id: 'ann' }, env }))[0], 400);
  assert.equal((await call('POST', { body: { kind: 'contributor', id: 'ann' }, origin: 'https://evil.example', env }))[0], 403);
  assert.equal((await call('GET', { query: '?kind=x', env }))[0], 400);
  assert.equal(env.HUB_STARS.writes, 0);
});

test('an IPv6 /64 is one source (rotating addresses cannot re-star)', async () => {
  assert.equal(sourceKey('2a09:bac5:1b2b:db9::15e:ce'), '2a09:bac5:1b2b:db9::/64');
  assert.equal(sourceKey('2a09:bac5:1b2b:0db9:1:2:3:4'), '2a09:bac5:1b2b:db9::/64');
  assert.equal(sourceKey('2001:db8::1'), '2001:db8:0:0::/64');
  assert.equal(sourceKey('::ffff:1.2.3.4'), '1.2.3.4');
  assert.equal(sourceKey('1.2.3.4'), '1.2.3.4');
  const env = { HUB_STARS: r2(), ASSETS };
  let [, b] = await call('POST', { body: { kind: 'corpus', id: 'aider' }, ip: '2a09:bac5:1b2b:db9::15e:ce', env });
  assert.equal(b.count, 1);
  [, b] = await call('POST', { body: { kind: 'corpus', id: 'aider' }, ip: '2a09:bac5:1b2b:db9::99:1', env });
  assert.equal(b.already, true); assert.equal(b.count, 1);
  [, b] = await call('GET', { query: '?kind=corpus&id=aider', ip: '2a09:bac5:1b2b:db9::abcd', env });
  assert.equal(b.starred, true);
});
