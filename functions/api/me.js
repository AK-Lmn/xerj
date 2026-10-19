// GET /api/me — who is signed in, and whether sign-in is offered at all.
//
//   { ok, enabled, providers: {github, hf}, user: null | {provider, login, name, avatar},
//     links: [{href, label}] }   pages for the signed-in user (header menu)
//
// enabled:false (no HUB_SESSION_SECRET, or no provider with both client id and
// secret) means the pages keep the Sign in button hidden. The provider user id
// stays inside the signed cookie; the page never needs it.
import { config, currentUser, json } from '../_lib/session.js';

export async function onRequestGet({ request, env }) {
  const c = config(env);
  if (!c.enabled) return json({ ok: true, enabled: false, providers: { github: false, hf: false }, user: null });
  const u = await currentUser(request, env);
  return json({
    ok: true, enabled: true, providers: c.providers,
    user: u ? { provider: u.provider, login: u.login, name: u.name, avatar: u.avatar } : null,
    links: u ? [{ href: '/me.html', label: 'My stars' }] : [],
  });
}
