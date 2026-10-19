"""Contributor pages for hub.xerj.org: one GitHub-profile-style page per author
who agreed to contribute, a wall of all of them, and a README badge each.

Source: tools/xerj-code/hub/candidates/authors/CONTRIBUTORS.jsonl (written by
the outreach pipeline; one row per approved contribution). Every number on a
page is read from that ledger or the registry; a number we do not have is left off the page,
never estimated. There is no per-author retrieval counter yet (nothing here is
live), so the pages show no retrieval figure at all rather than a placeholder.

  out/contributors/index.html          the wall
  out/contributors/<login>.html        one author
  out/contributors/<login>/badge.svg   "XERJ Corpus Hub | contributor" badge
"""
import json, pathlib, re, urllib.parse, collections

LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")   # GitHub's login alphabet: safe as a file name
SITE = "https://hub.xerj.org"

STYLE = """
/* contributor pages */
.cwrap{max-width:1180px;margin:0 auto;padding:var(--sp-10) var(--page-x)}
.prof{display:grid;grid-template-columns:240px 1fr;gap:var(--sp-10);align-items:start}
.prof .av{width:240px;height:240px;border-radius:50%;border:1px solid var(--z-line);background:#fff;display:block}
.prof h1{font-family:var(--font-display);font-weight:900;font-size:var(--fs-56);line-height:1;margin:0 0 var(--sp-2)}
.prof .login{font-family:var(--font-mono);color:var(--z-mute);font-size:var(--fs-20)}
.prof .login a{text-decoration:none}
.ribbon{display:inline-block;margin:var(--sp-4) 0;font-family:var(--font-data);font-size:var(--fs-11);font-weight:700;
text-transform:uppercase;letter-spacing:var(--track-ui);color:#fff;padding:.5em 1em;
background:linear-gradient(100deg,#6d28d9,#9333ea,#7c3aed,#6d28d9);background-size:280% 100%;animation:ctaflow 5s ease infinite}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--z-line);border:1px solid var(--z-line);margin:var(--sp-6) 0}
.kpi{background:#fff;padding:var(--sp-5)}
.kpi b{display:block;font-family:var(--font-display);font-weight:800;font-size:var(--fs-32);line-height:1.1}
.kpi span{font-family:var(--font-data);font-size:var(--fs-11);text-transform:uppercase;letter-spacing:var(--track-label);color:var(--z-mute)}
.kpi.pending b{color:var(--z-mute);font-size:var(--fs-20);padding-top:.35em}
.contrib{border:1px solid var(--z-line);background:#fff;padding:var(--sp-5) var(--sp-6);margin:var(--sp-4) 0}
.contrib h3{margin:0 0 var(--sp-2);font-family:var(--font-data);font-size:var(--fs-20)}
.contrib h3 a{text-decoration:none}
.contrib .stars{float:right;font-family:var(--font-data);font-weight:600;color:var(--z-accent)}
.contrib .commit{font-family:var(--font-mono);font-size:var(--fs-13);color:var(--z-mute);margin:var(--sp-2) 0}
.chips{display:flex;flex-wrap:wrap;gap:var(--sp-2);margin-top:var(--sp-3)}
.chip{font-family:var(--font-data);font-size:var(--fs-11);text-transform:uppercase;letter-spacing:var(--track-label);
border:1px solid var(--z-line);padding:.25em .6em;color:var(--z-mute)}
.chip.ok{color:var(--ok);border-color:var(--ok)}.chip.warn{color:var(--warn);border-color:var(--warn)}
.share{display:flex;gap:var(--sp-3);flex-wrap:wrap;margin:var(--sp-6) 0}
.share a,.share button{font-family:var(--font-data);font-size:var(--fs-11);font-weight:600;text-transform:uppercase;
letter-spacing:var(--track-ui);text-decoration:none;color:var(--z-ink);border:1px solid var(--z-ink);background:none;padding:.6em 1em;cursor:pointer}
.share a:hover,.share button:hover{background:var(--z-ink);color:#fff}
.badgebox{border:1px solid var(--z-line);background:#fff;padding:var(--sp-4) var(--sp-5);margin:var(--sp-4) 0}
.badgebox pre{font-family:var(--font-mono);font-size:var(--fs-13);white-space:pre-wrap;word-break:break-all;margin:var(--sp-3) 0 0}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:var(--sp-3);margin-top:var(--sp-6)}
.wall a{display:flex;gap:var(--sp-3);align-items:center;border:1px solid var(--z-line);background:#fff;padding:var(--sp-3);text-decoration:none}
.wall img{width:44px;height:44px;border-radius:50%}
.wall b{display:block;font-family:var(--font-data);font-size:var(--fs-13)}
.wall span{font-family:var(--font-mono);font-size:var(--fs-11);color:var(--z-mute)}
.whead h1{font-family:var(--font-display);font-weight:900;font-size:var(--fs-96);line-height:.95;margin:0}
.whead p{max-width:760px;color:var(--z-mute)}
@media (max-width:820px){.prof{grid-template-columns:1fr}.prof .av{width:140px;height:140px}.kpis{grid-template-columns:repeat(2,1fr)}.whead h1{font-size:var(--fs-56)}}
"""

COPY_BADGE_JS = """<script>
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
  navigator.clipboard.writeText(document.getElementById(b.dataset.copy).innerText).then(function(){var t=b.innerText;b.innerText='COPIED';setTimeout(function(){b.innerText=t},1400)})})});
</script>"""


def load(hub_dir):
    p = pathlib.Path(hub_dir) / "candidates" / "authors" / "CONTRIBUTORS.jsonl"
    if not p.exists():
        return {}
    people = collections.defaultdict(list)
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        login = (r.get("contributor") or {}).get("login") or ""
        if LOGIN_RE.match(login):
            people[login].append(r)
    return people


def badge_svg(label="XERJ Corpus Hub", value="contributor"):
    # shields-style flat badge; widths from a fixed 6.6 px/char estimate for 11px Verdana
    lw, vw = int(len(label) * 6.6) + 14, int(len(value) * 6.6) + 14
    w = lw + vw
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="{label}: {value}">'
            f'<title>{label}: {value}</title><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
            f'<stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>'
            f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#11120f"/><rect x="{lw}" width="{vw}" height="20" fill="#7c3aed"/>'
            f'<rect width="{w}" height="20" fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
            f'<text x="{lw / 2:.0f}" y="14">{label}</text><text x="{lw + vw / 2:.0f}" y="14">{value}</text></g></svg>')


def _n(x):
    return f"{x:,}" if isinstance(x, int) else "—"


def person_body(login, rows, esc, live_slugs):
    rows = sorted(rows, key=lambda r: -(r.get("repo_stars") or 0))
    c0 = rows[0]["contributor"]
    name = c0.get("name") or login
    stars = sum(r.get("repo_stars") or 0 for r in rows)
    lines = sum((r.get("contribution") or {}).get("lines") or 0 for r in rows)
    first = min(r["consent"]["at"] for r in rows)
    url = f"{SITE}/contributors/{login}.html"
    repos = ", ".join(r["repo"] for r in rows[:2])
    tweet = f"My work in {repos} was selected for the XERJ Corpus Hub: AI coding agents retrieve it as a worked reference instead of guessing. {url}"
    cards = []
    for r in rows:
        k = r.get("contribution") or {}
        lic = r.get("licence") or {}
        status = ('<span class="chip ok">live in the hub</span>' if r["corpus"] in live_slugs
                  else '<span class="chip warn">selected · in licence review</span>')
        commit = (f'<div class="commit"><a href="{esc(k["commit_url"])}">{esc(k["commit"][:10])}</a> {esc(k.get("title") or "")}</div>'
                  if k.get("commit") else "")
        size = " · ".join(x for x in [f'{k["files"]} files' if k.get("files") else "", f'{_n(k.get("lines"))} lines' if k.get("lines") else "",
                                         ", ".join(k.get("langs") or [])] if x)
        chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in (r.get("topics") or [])[:6])
        cards.append(f"""<div class="contrib"><span class="stars">★ {_n(r.get("repo_stars"))}</span>
<h3><a href="{esc(r["repo_url"])}">{esc(r["repo"])}</a></h3>{commit}
<div class="commit">{esc(size)}{" · " + esc(", ".join(k.get("areas") or [])[:120]) if k.get("areas") else ""}</div>
<div class="chips">{status}<span class="chip">{esc(r.get("shelf") or "")}</span><span class="chip">{esc(lic.get("spdx") or "")}</span>{chips}
<span class="chip">agreed {esc(r["consent"]["at"][:10])}</span></div></div>""")
    md = f"[![XERJ Corpus Hub contributor]({SITE}/contributors/{login}/badge.svg)]({url})"
    return f"""<main class="cwrap">
<section class="prof"><img class="av" src="https://github.com/{esc(login)}.png?size=480" alt="{esc(name)}">
<div><h1>{esc(name)}</h1><div class="login"><a href="https://github.com/{esc(login)}">@{esc(login)}</a></div>
<div class="ribbon">Corpus Hub contributor since {esc(first[:10])}</div>
<p>{esc(name)}'s work was selected for the XERJ Corpus Hub, the open reference memory AI coding agents search before they write code.
When an agent meets the same problem, it gets this implementation back as a worked example, with the author and the repository attached.</p>
<div class="kpis"><div class="kpi"><b>{len(rows)}</b><span>contribution{"s" if len(rows) != 1 else ""}</span></div>
<div class="kpi"><b>★ {_n(stars)}</b><span>GitHub stars on the repo{"s" if len(rows) != 1 else ""}</span></div>
<div class="kpi"><b>{_n(lines) if lines else "—"}</b><span>lines in the selected work</span></div></div>
<div class="share"><a href="https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet)}" target="_blank" rel="noopener">Share on X</a>
<a href="https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(url)}" target="_blank" rel="noopener">Share on LinkedIn</a>
<a href="https://news.ycombinator.com/submitlink?u={urllib.parse.quote(url)}&t={urllib.parse.quote(name + ' on the XERJ Corpus Hub')}" target="_blank" rel="noopener">Hacker News</a>
<button data-copy="badge-{esc(login)}">Copy README badge</button></div>
</div></section>
<h2>Selected work</h2>{"".join(cards)}
<div class="badgebox"><img src="{esc(login)}/badge.svg" alt="XERJ Corpus Hub contributor badge">
<pre id="badge-{esc(login)}">{esc(md)}</pre></div>
<p style="color:var(--z-mute);font-size:var(--fs-13)">Included with the author's permission (email, {esc(first[:10])}), under each repository's own licence, with attribution.
Want it removed? Reply to the email or open an issue on <a href="https://github.com/xerj-org/xerj">xerj-org/xerj</a>.</p>
</main>{COPY_BADGE_JS}"""


def wall_body(people, esc):
    order = sorted(people.items(), key=lambda kv: -sum(r.get("repo_stars") or 0 for r in kv[1]))
    tiles = "".join(f'<a href="{esc(l)}.html"><img src="https://github.com/{esc(l)}.png?size=88" alt="" loading="lazy">'
                    f'<div><b>{esc(rs[0]["contributor"].get("name") or l)}</b><span>@{esc(l)} · {esc(rs[0]["repo"])}</span></div></a>'
                    for l, rs in order)
    repos = len({r["repo"] for rs in people.values() for r in rs})
    return f"""<main class="cwrap"><section class="whead"><h1>The people behind the hub</h1>
<p>{len(people):,} developers agreed to let AI agents learn from their work: {repos:,} repositories, each included with the author's permission,
under its own licence, with attribution. When an agent hits the same problem, it builds on their solution instead of guessing.</p>
<a class="cta" href="../contribute.html">Add yours</a></section><div class="wall">{tiles}</div></main>"""


def og(html, title, desc, url, image):
    tags = (f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">'
            f'<meta property="og:url" content="{url}"><meta property="og:image" content="{image}">'
            f'<meta name="twitter:card" content="summary"><link rel="canonical" href="{url}">')
    return html.replace("</head>", tags + "</head>", 1)


def generate(out, hub_dir, page, esc, live_slugs):
    people = load(hub_dir)
    if not people:
        return 0
    d = pathlib.Path(out) / "contributors"
    d.mkdir(exist_ok=True)
    for login, rows in people.items():
        name = rows[0]["contributor"].get("name") or login
        title = f"{name} (@{login}): XERJ Corpus Hub contributor"
        desc = f"{name}'s work in {rows[0]['repo']} is in the XERJ Corpus Hub, the reference memory AI coding agents search before writing code."
        html = page(title, desc, person_body(login, rows, esc, live_slugs), rel="../")
        (d / f"{login}.html").write_text(og(html, esc(title), esc(desc), f"{SITE}/contributors/{login}.html", f"https://github.com/{login}.png?size=400"))
        (d / login).mkdir(exist_ok=True)
        (d / login / "badge.svg").write_text(badge_svg())
    html = page("Contributors: XERJ Corpus Hub", "The developers whose work AI agents retrieve from the XERJ Corpus Hub", wall_body(people, esc), rel="../")
    (d / "index.html").write_text(og(html, "The people behind the XERJ Corpus Hub", "Developers who agreed to let AI agents learn from their work",
                                     f"{SITE}/contributors/", "https://github.com/xerj-org.png"))
    return len(people)
