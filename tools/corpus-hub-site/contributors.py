"""Contributor pages for hub.xerj.org: one GitHub-profile-style page per author
who agreed to contribute, a wall of all of them, and a README badge each.

Sources: tools/xerj-code/hub/candidates/authors/CONTRIBUTORS.jsonl (written by
the outreach pipeline; one row per approved contribution), the themed candidate
corpora's CONTRIBUTORS-2026-10.md, and the registry manifests. A person is one
login however many corpora they appear in (see load()). Every number on a
page is read from those files; a number we do not have is left off the page,
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
.kpis{display:flex;flex-wrap:wrap;gap:1px;background:var(--z-line);border:1px solid var(--z-line);margin:var(--sp-6) 0}
.kpi{flex:1 1 150px;background:#fff;padding:var(--sp-5)}
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
.hubstar[hidden]{display:none}
section.more[hidden],.signin-hint[hidden]{display:none}
section.more{margin:var(--sp-8) 0}
.signin-hint{border:1px dashed var(--z-line);padding:var(--sp-3) var(--sp-5);color:var(--z-mute);font-size:var(--fs-13);background:#fff}
.moretable{width:100%;border-collapse:collapse;margin:var(--sp-3) 0;font-size:var(--fs-13);background:#fff}
.moretable th,.moretable td{border:1px solid var(--z-line);padding:var(--sp-1) var(--sp-3);text-align:left;vertical-align:top;word-break:break-word}
.moretable th:empty{display:none}
.thisisme{border:2px solid var(--z-accent);background:#fff;padding:var(--sp-5) var(--sp-6);margin:var(--sp-4) 0}
.thisisme h2{margin-top:0}
.kpi.hubstar b [data-n]{font:inherit;color:inherit;letter-spacing:normal;text-transform:none}
.hubstar button{margin-top:var(--sp-2);font-family:var(--font-data);font-size:var(--fs-11);font-weight:700;text-transform:uppercase;
letter-spacing:var(--track-ui);border:1px solid var(--z-accent);color:var(--z-accent);background:none;padding:.35em .8em;cursor:pointer}
.hubstar button[disabled]{opacity:.6;cursor:default}
.hubstar.inline{display:inline-flex;gap:var(--sp-3);align-items:center;border:1px solid var(--z-line);background:#fff;padding:var(--sp-2) var(--sp-4);margin:var(--sp-3) 0}
.hubstar.inline b{font-family:var(--font-data)}.hubstar.inline button{margin:0}
@media (max-width:820px){.prof{grid-template-columns:1fr}.prof .av{width:140px;height:140px}.kpi{flex-basis:40%}.whead h1{font-size:var(--fs-56)}}
"""

COPY_BADGE_JS = """<script>
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
  navigator.clipboard.writeText(document.getElementById(b.dataset.copy).innerText).then(function(){var t=b.innerText;b.innerText='COPIED';setTimeout(function(){b.innerText=t},1400)})})});
</script>"""


THEMED_MD = "CONTRIBUTORS-2026-10.md"
# | [owner/repo](url) | @login | [sha10](commit_url) title | SPDX | YYYY-MM-DD |
THEMED_ROW = re.compile(r"^\| \[([^\]]+)\]\((https://github\.com/[^)]+)\) \| @([A-Za-z0-9-]+) \| "
                        r"\[([0-9a-f]{7,40})\]\(([^)]+)\) ?(.*?) \| ([^|]*) \| (\d{4}-\d{2}-\d{2}) \|$")
GH_OWNER = re.compile(r"^https://github\.com/([A-Za-z0-9-]+)/", re.I)


def _reviewed(review):
    """A source counts as licence-reviewed only when its review block records a
    verdict (use is not UNREVIEWED) and who made it. Never inferred."""
    use = (review or {}).get("use", "UNREVIEWED")
    return bool(use and use != "UNREVIEWED" and (review or {}).get("by"))


def _person(people, login, name=""):
    key = login.lower()                    # GitHub logins are case-insensitive
    if key not in people:
        people[key] = {"login": login, "name": name, "work": {}, "corpora": {}, "agreed": []}
    elif name and not people[key]["name"]:
        people[key]["name"] = name
    return people[key]


def load(hub_dir, registry=None):
    """Every contributor who agreed by email, keyed on login (case-insensitive),
    with their contributions gathered from EVERY corpus they appear in:

      * candidates/authors/CONTRIBUTORS.jsonl  one corpus per approved repo
      * candidates/CONTRIBUTORS-2026-10.md     authors in the themed candidate
                                               corpora (agent-engineering, ...)
      * the registry's lane-A manifests        corpora that pin a repository
                                               the contributor owns

    A contribution is one selected commit; the same commit reached through two
    corpora is counted once (files and lines too), but both corpora are listed.
    `registry` is gen.load_registry()'s list; only its slug/status/repos are used.
    """
    hub = pathlib.Path(hub_dir)
    people = {}
    ledger = hub / "candidates" / "authors" / "CONTRIBUTORS.jsonl"
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            c = r.get("contributor") or {}
            login = c.get("login") or ""
            if not LOGIN_RE.match(login):
                continue
            pp = _person(people, login, c.get("name") or "")
            k = r.get("contribution") or {}
            lic = r.get("licence") or {}
            key = (k.get("commit") or f'{r["corpus"]}:nocommit').lower()
            w = pp["work"].setdefault(key, {
                "repo": r.get("repo", ""), "repo_url": r.get("repo_url", ""), "repo_stars": r.get("repo_stars"),
                "commit": k.get("commit") or "", "commit_url": k.get("commit_url") or "", "title": k.get("title") or "",
                "files": k.get("files"), "lines": k.get("lines"), "langs": k.get("langs") or [], "areas": k.get("areas") or [],
                "topics": r.get("topics") or [], "shelf": r.get("shelf") or "", "spdx": lic.get("spdx") or "",
                "reviewed": lic.get("reviewed") is True, "agreed": (r.get("consent") or {}).get("at", ""), "corpora": [],
                "committed_at": k.get("committed_at") or "", "suggested_use": lic.get("suggested_use") or "",
                "pin": (r.get("pin") or {}).get("sha") or "",
            })
            if r["corpus"] not in w["corpora"]:
                w["corpora"].append(r["corpus"])
            pp["corpora"].setdefault(r["corpus"], "author corpus")
            if w["agreed"]:
                pp["agreed"].append(w["agreed"])
    md = hub / "candidates" / THEMED_MD
    if md.exists():
        corpus = None
        for line in md.read_text().splitlines():
            if line.startswith("## "):
                corpus = line[3:].split(" (")[0].strip()
                continue
            m = THEMED_ROW.match(line.strip())
            if not (m and corpus):
                continue
            repo, url, login, sha, curl, title, spdx, date = m.groups()
            if not LOGIN_RE.match(login):
                continue
            pp = _person(people, login)
            manifest = hub / "candidates" / f"{corpus}.json"
            review = {}
            if manifest.exists():
                for src in json.loads(manifest.read_text()).get("repos", []):
                    if src.get("url", "").rstrip("/").lower() == url.rstrip("/").lower():
                        review = src.get("review") or {}
            # an abbreviated sha in the table matches the ledger's full sha
            key = next((k for k in pp["work"] if k.startswith(sha.lower())), sha.lower())
            w = pp["work"].setdefault(key, {
                "repo": repo, "repo_url": url, "repo_stars": None, "commit": sha, "commit_url": curl,
                "title": title.strip(), "files": None, "lines": None, "langs": [], "areas": [], "topics": [],
                "shelf": "", "spdx": spdx.strip(), "reviewed": _reviewed(review), "agreed": date, "corpora": [],
                "committed_at": "", "suggested_use": review.get("use", "") if _reviewed(review) else "", "pin": "",
            })
            if corpus not in w["corpora"]:
                w["corpora"].append(corpus)
            pp["corpora"].setdefault(corpus, "candidate corpus")
            pp["agreed"].append(date)
    # corpora in the registry that pin a repository the contributor owns
    for c in registry or []:
        for src in c.get("repos") or []:
            m = GH_OWNER.match(src.get("url", ""))
            if m and m.group(1).lower() in people:
                people[m.group(1).lower()]["corpora"][c["slug"]] = c.get("status") or "registry"
    return {pp["login"]: pp for pp in people.values() if pp["work"]}


def volume(pp, live_slugs=()):
    """The numbers on a profile, all summed over distinct commits / repos."""
    work = list(pp["work"].values())
    stars_by_repo = {}
    for w in work:
        if isinstance(w.get("repo_stars"), int):
            stars_by_repo[w["repo_url"].lower()] = w["repo_stars"]
    return {
        "commits": sum(1 for w in work if w["commit"]),
        "files": sum(w["files"] for w in work if isinstance(w.get("files"), int)),
        "lines": sum(w["lines"] for w in work if isinstance(w.get("lines"), int)),
        "corpora": len(pp["corpora"]),
        "live": sorted(s for s in pp["corpora"] if s in live_slugs),
        "repos": len({w["repo_url"].lower() for w in work}),
        "gh_stars": sum(stars_by_repo.values()),
        "since": min(pp["agreed"]) if pp["agreed"] else "",
    }


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


def person_body(pp, esc, live_slugs, pages=()):
    login = pp["login"]
    work = sorted(pp["work"].values(), key=lambda w: (-(w.get("repo_stars") or 0), w["repo"].lower()))
    name = pp["name"] or login
    v = volume(pp, live_slugs)
    url = f"{SITE}/contributors/{login}.html"
    repos = ", ".join(w["repo"] for w in work[:2])
    tweet = f"My work in {repos} was selected for the XERJ Corpus Hub: AI coding agents retrieve it as a worked reference instead of guessing. {url}"
    cards = []
    for w in work:
        live = [c for c in w["corpora"] if c in live_slugs]
        status = ('<span class="chip ok">live in the hub</span>' if live
                  else '<span class="chip warn">selected · in licence review</span>')
        # issue #1890: a corpus still in review has no manifest in the registry, so
        # the documented install path (llms.txt step 3) 404s. Say so on the card.
        pending = ("" if live else
                   '<p class="note pending">Not installable yet: this corpus is not in the hub registry until its '
                   'licence review passes, so <code>xerj corpus add</code> and <code>xerj ask</code> cannot fetch it. '
                   'It becomes installable when this card says live in the hub.</p>')
        commit = (f'<div class="commit"><a href="{esc(w["commit_url"])}">{esc(w["commit"][:10])}</a> {esc(w["title"])}</div>'
                  if w["commit"] else "")
        size = " · ".join(x for x in [f'{w["files"]} files' if w.get("files") else "", f'{_n(w.get("lines"))} lines' if w.get("lines") else "",
                                         ", ".join(w["langs"])] if x)
        chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in w["topics"][:6])
        corp = "".join(f'<a class="chip" href="../corpus/{esc(c)}.html">corpus {esc(c)}</a>' if c in pages
                       else f'<span class="chip">corpus {esc(c)}</span>' for c in w["corpora"])
        gh = f'<span class="stars" title="GitHub stars on the repository">GitHub ★ {_n(w.get("repo_stars"))}</span>' if isinstance(w.get("repo_stars"), int) else ""
        cards.append(f"""<div class="contrib">{gh}
<h3><a href="{esc(w["repo_url"])}">{esc(w["repo"])}</a></h3>{commit}
<div class="commit">{"selected commit: " + esc(size) if size else ""}{" · " + esc(", ".join(w["areas"])[:120]) if w["areas"] else ""}</div>
<p class="note">The corpus is the whole repository at the pinned commit, not only the files of the selected commit.</p>
<div class="chips">{status}{corp}{f'<span class="chip">{esc(w["shelf"])}</span>' if w["shelf"] else ""}<span class="chip">{esc(w["spdx"])}</span>{chips}
<span class="chip">agreed {esc(w["agreed"][:10])}</span></div>{pending}</div>""")
    other = sorted(c for c in pp["corpora"] if not any(c in w["corpora"] for w in work))
    also = ""
    if other:
        links = ", ".join(f'<a href="../corpus/{esc(c)}.html">{esc(c)}</a>' if c in pages else esc(c) for c in other)
        also = f'<p class="note">Their repositories are also pinned in: {links}.</p>'
    md = f"[![XERJ Corpus Hub contributor]({SITE}/contributors/{login}/badge.svg)]({url})"
    kpi = lambda val, label: f'<div class="kpi"><b>{val}</b><span>{label}</span></div>'
    s_ = lambda n, w: w if n == 1 else w + "s"
    kpis = (kpi(v["corpora"], s_(v["corpora"], "corpus").replace("corpuss", "corpora"))
            + kpi(v["commits"], s_(v["commits"], "selected commit"))
            + (kpi(_n(v["files"]), s_(v["files"], "file")) if v["files"] else "")
            + (kpi(_n(v["lines"]), s_(v["lines"], "line")) if v["lines"] else "")
            + (kpi("★ " + _n(v["gh_stars"]), "GitHub stars on " + s_(v["repos"], "repo")) if v["gh_stars"] else "")
            + star_widget("contributor", login, esc))
    return f"""<main class="cwrap">
<section class="prof"><img class="av" src="https://github.com/{esc(login)}.png?size=480" alt="{esc(name)}">
<div><h1>{esc(name)}</h1><div class="login"><a href="https://github.com/{esc(login)}">@{esc(login)}</a></div>
<div class="ribbon">Corpus Hub contributor since {esc(v["since"][:10])}</div>
<p>{esc(name)}'s work was selected for the XERJ Corpus Hub, the open reference memory AI coding agents search before they write code.
When an agent meets the same problem, it gets this implementation back as a worked example, with the author and the repository attached.</p>
<div class="kpis">{kpis}</div>
<p class="note">Totals across every corpus @{esc(login)} appears in; a commit selected for two corpora counts once. Files and lines count the selected commits; each corpus indexes the whole repository at its pinned commit.</p>
<div class="share"><a href="https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet)}" target="_blank" rel="noopener">Share on X</a>
<a href="https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(url)}" target="_blank" rel="noopener">Share on LinkedIn</a>
<a href="https://news.ycombinator.com/submitlink?u={urllib.parse.quote(url)}&t={urllib.parse.quote(name + ' on the XERJ Corpus Hub')}" target="_blank" rel="noopener">Hacker News</a>
<button data-copy="badge-{esc(login)}">Copy README badge</button></div>
</div></section>
<h2>Selected work</h2>{"".join(cards)}{also}
{more_block("contributor", login, esc)}
<div class="badgebox"><img src="{esc(login)}/badge.svg" alt="XERJ Corpus Hub contributor badge">
<pre id="badge-{esc(login)}">{esc(md)}</pre></div>
<p style="color:var(--z-mute);font-size:var(--fs-13)">Included with the author's permission (email, {esc(v["since"][:10])}), under each repository's own licence, with attribution.
Want it removed? Reply to the email or open an issue on <a href="https://github.com/xerj-org/xerj">xerj-org/xerj</a>.</p>
</main>{COPY_BADGE_JS}{STARS_JS}{MORE_JS}"""


# Hub stars: counts and the Star button come from /api/hub-stars
# (functions/api/hub-stars.js). The control ships hidden and is shown only when
# the endpoint answers enabled:true, so a site without the R2 binding shows
# no star figure at all rather than a fake zero.
STARS_JS = """<script>
(function(){
  var API='/api/hub-stars';
  function fmt(n){return Number(n).toLocaleString('en-US')}
  document.querySelectorAll('.hubstar[data-kind]').forEach(function(el){
    var kind=el.dataset.kind,id=el.dataset.id,num=el.querySelector('[data-n]'),btn=el.querySelector('button');
    function show(r){num.textContent=fmt(r.count||0);if(r.starred){btn.disabled=true;btn.textContent='Starred'}el.hidden=false}
    fetch(API+'?kind='+kind+'&id='+encodeURIComponent(id)).then(function(r){return r.json()}).then(function(r){
      if(!r||!r.ok||!r.enabled)return; show(r);
      btn.addEventListener('click',function(){btn.disabled=true;
        fetch(API,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({kind:kind,id:id})})
          .then(function(r){return r.json()}).then(function(r){if(r&&r.ok)show(r);else{btn.disabled=false;btn.title=(r&&r.error)||''}})
          .catch(function(){btn.disabled=false})});
    }).catch(function(){});
  });
  var wall=document.querySelector('.wall[data-stars]');
  if(wall)fetch(API+'?kind='+wall.dataset.stars).then(function(r){return r.json()}).then(function(r){
    if(!r||!r.ok||!r.enabled)return;
    wall.querySelectorAll('[data-id]').forEach(function(a){var n=r.counts[a.dataset.id]||0,s=a.querySelector('.hs');
      s.textContent=' · hub ★ '+fmt(n);s.hidden=false});
  }).catch(function(){});
})();
</script>"""


# Signed-in extras (functions/api/v1/contributors/[login].js, functions/api/v1/corpus/[slug].js).
# The static page carries only this empty block. Anonymous visitors on a hub with
# sign-in enabled see one "Sign in to see more" line; with sign-in disabled the
# block stays hidden and the page is exactly what it was. The details are fetched
# from the authenticated API after sign-in and never baked into the HTML.
MORE_HINT = {
    "contributor": "Sign in with GitHub or Hugging Face to see more: every selected commit in full "
                   "(commit date, every folder, licence review state, pin) and the pack builds of each corpus.",
    "corpus": "Sign in with GitHub or Hugging Face to see more: this corpus's pack build and pin history, "
              "full source pins and review records, and how its packs are signed.",
}


def more_block(kind, sid, esc):
    return (f'<section class="more" data-more="{kind}" data-id="{esc(sid)}" hidden>'
            f'<p class="signin-hint">{esc(MORE_HINT[kind])}</p><div class="more-body"></div></section>')


MORE_JS = """<script>
(function(){
  var sec=document.querySelector('section.more[data-more]'); if(!sec) return;
  var kind=sec.dataset.more,id=sec.dataset.id,hint=sec.querySelector('.signin-hint'),body=sec.querySelector('.more-body');
  function el(t,a,txt){var e=document.createElement(t);for(var k in a)if(a[k]!=null)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e}
  function add(p,c){p.appendChild(c);return c}
  function fmt(n){return typeof n==='number'?n.toLocaleString('en-US'):''}
  function mb(n){return typeof n==='number'?(n/1048576).toFixed(1)+' MB':''}
  function link(href,txt){return href?el('a',{href:href,rel:'noopener'},txt):el('span',{},txt)}
  function table(head,rows){var t=el('table',{'class':'moretable'}),tr=add(t,el('tr'));
    head.forEach(function(h){add(tr,el('th',{},h))});
    rows.forEach(function(r){var tr=add(t,el('tr'));r.forEach(function(c){var td=add(tr,el('td'));if(c&&c.nodeType)td.appendChild(c);else td.textContent=c==null?'':String(c)})});
    return t}
  function rel(tag){return tag?link('https://github.com/xerj-org/xerj/releases/tag/'+encodeURIComponent(tag),tag):''}
  function build(b){if(!b)return '';var s=el('span');add(s,link(b.url,(b.date||'')+' '+(b.result||'')));if(b.tag){s.appendChild(document.createTextNode(' · '));add(s,rel(b.tag))}return s}
  function contributor(r){
    var c=r.contributor;
    if(r.is_me){
      var me=add(body,el('div',{'class':'thisisme'}));
      add(me,el('h2',{},'This is you'));
      var live=0,review=0;c.work.forEach(function(w){(w.corpora||[]).forEach(function(x){if(x.status==='live')live++;else review++})});
      add(me,el('p',{},'You are signed in as @'+c.login+'. '+c.work.length+' of your commits are selected; '+live+' corpus entr'+(live===1?'y is':'ies are')+' live and '+review+' '+(review===1?'is':'are')+' still in licence review. Each card below shows where your work is and its last pack build.'));
      var a=add(me,el('p',{}));
      add(a,link('https://github.com/xerj-org/xerj/issues/new?title='+encodeURIComponent('Corpus Hub: change or remove my work (@'+c.login+')'),'Ask for a change or removal'));
      a.appendChild(document.createTextNode(' · '));add(a,link('/me.html','Your hub stars'));
    }
    add(body,el('h2',{},'Every selected commit'));
    c.work.forEach(function(w){
      var d=add(body,el('div',{'class':'contrib'}));
      var h=add(d,el('h3'));add(h,link(w.repo_url,w.repo));
      var cm=add(d,el('div',{'class':'commit'}));add(cm,link(w.commit_url,w.commit||'no commit'));
      cm.appendChild(document.createTextNode(' '+(w.title||'')));
      var rows=[['committed',(w.committed_at||'').replace('T',' ').replace('Z',' UTC')],['pinned at',w.pin],
        ['size',[w.files?fmt(w.files)+' files':'',w.lines?fmt(w.lines)+' lines':''].filter(Boolean).join(' · ')],
        ['languages',(w.langs||[]).join(', ')],['folders',(w.areas||[]).join(', ')],['topics',(w.topics||[]).join(', ')],
        ['licence',[w.spdx,w.suggested_use,w.reviewed?'licence reviewed':'licence review pending'].filter(Boolean).join(' · ')],
        ['agreed',w.agreed]].filter(function(x){return x[1]});
      add(d,table(['',''],rows));
      if(w.corpora&&w.corpora.length)add(d,table(['corpus','status','manifest','last pack build'],w.corpora.map(function(x){
        return [x.page?link('/corpus/'+x.slug+'.html',x.slug):x.slug,x.status||'candidate',x.manifest||'',build(x.last_build)]})));
    });
    var also=Object.keys(c.also_pinned_in||{});
    if(also.length)add(body,el('p',{'class':'note'},'Repositories of yours are also pinned in: '+also.join(', ')+'.'));
  }
  function corpus(r){
    var c=r.corpus;
    if(c.builds&&c.builds.length){
      add(body,el('h2',{},'Pack builds'));
      add(body,table(['date','run','pin','result','pack size','definitions','release / error'],c.builds.map(function(b){
        return [b.date,link(b.url,b.run),b.pin8,b.result,mb(b.bytes),fmt(b.defs),b.tag?rel(b.tag):[b.stage,b.error].filter(Boolean).join(': ')]})));
    }
    if(c.pins&&c.pins.length){
      add(body,el('h2',{},'Pin history'));
      add(body,table(['pin','first build','last build','builds','published'],c.pins.map(function(p){return [p.pin8,p.first,p.last,p.builds,p.published?rel(p.published):'not yet']})));
    }
    if(r.catalogue){var e=r.catalogue;add(body,el('h2',{},'Signed pack in the catalogue'));
      add(body,table(['',''],[['pack',link(e.pack_url,e.pack_url)],['size',mb(e.pack_bytes||e.bytes)],['sha256',e.pack_sha256],['signature',link(e.sig_url,e.sig_url)]].filter(function(x){return x[1]})))}
    add(body,el('h2',{},'Signing'));
    var sg=[['scheme',r.signing.scheme],['hub key (ed25519)',r.signing.hub_pubkey]];if(c.pack_pubkey)sg.push(['pack key',c.pack_pubkey]);
    add(body,table(['',''],sg.filter(function(x){return x[1]})));
    if(c.repos&&c.repos.length){add(body,el('h2',{},'Sources, full pins and review records'));
      add(body,table(['source','pin','files','size','licence','review'],c.repos.map(function(x){var v=x.review||{};
        return [link((x.url||'').replace(/\\.git$/,''),x.repo),x.sha,fmt(x.files),mb(x.bytes),v.spdx||x.licence||'',[v.use,v.by,v.at].filter(Boolean).join(' · ')]})))}
    if(c.repos_summary){var s=c.repos_summary;add(body,el('p',{'class':'note'},s.count+' sources, '+fmt(s.files)+' files, '+mb(s.bytes)+'; '+s.reviewed+' with a recorded licence review ('+s.licences.join(', ')+').'))}
    if(c.pack_stats){add(body,el('h2',{},'Pack measurements'));
      add(body,table(['',''],Object.keys(c.pack_stats).filter(function(k){return typeof c.pack_stats[k]!=='object'}).map(function(k){return [k.replace(/_/g,' '),String(c.pack_stats[k])]})))}
    if(!body.childNodes.length)add(body,el('p',{'class':'note'},'No pack has been built for this corpus yet.'));
  }
  (window.hubMe=window.hubMe||fetch('/api/me',{credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).catch(function(){return null})).then(function(me){
    if(!me||!me.enabled)return;
    sec.hidden=false;
    if(!me.user)return;
    hint.hidden=true;
    fetch('/api/v1/'+(kind==='corpus'?'corpus':'contributors')+'/'+encodeURIComponent(id),{credentials:'same-origin'})
      .then(function(r){return r.json()}).then(function(r){
        if(!r||!r.ok){add(body,el('p',{'class':'note'},(r&&r.error)||'Details are not available right now.'));return}
        add(body,el('p',{'class':'note'},'Shown because you are signed in. Registry state as of '+(r.generated||'the last deploy')+'.'));
        if(kind==='corpus')corpus(r);else contributor(r);
      }).catch(function(){add(body,el('p',{'class':'note'},'Details are not available right now.'))});
  });
})();
</script>"""


def star_widget(kind, sid, esc, inline=False):
    """Hidden until /api/hub-stars says it is enabled; see STARS_JS."""
    sid = esc(sid.lower())
    if inline:
        return (f'<div class="hubstar inline" data-kind="{kind}" data-id="{sid}" hidden>'
                f'<b>hub ★ <span data-n>0</span></b><button type="button">Star this {kind}</button></div>')
    return (f'<div class="kpi hubstar" data-kind="{kind}" data-id="{sid}" hidden><b>★ <span data-n>0</span></b>'
            f'<span>hub stars</span><br><button type="button">Star</button></div>')


def stars_targets(people, registry):
    """The ids /api/hub-stars accepts: only pages this deploy actually has."""
    return {"contributor": sorted(l.lower() for l in people),
            "corpus": sorted(c["slug"].lower() for c in registry or []),
            # page file names keep the login's case; ids are lower-case
            "pages": {l.lower(): l for l in sorted(people) if l != l.lower()}}


def wall_body(people, esc, live_slugs=()):
    vols = {l: volume(pp, live_slugs) for l, pp in people.items()}
    order = sorted(people, key=lambda l: (-vols[l]["gh_stars"], l.lower()))
    tiles = "".join(f'<a href="{esc(l)}.html" data-id="{esc(l.lower())}"><img src="https://github.com/{esc(l)}.png?size=88" alt="" loading="lazy">'
                    f'<div><b>{esc(people[l]["name"] or l)}</b><span>@{esc(l)} · {vols[l]["corpora"]} corp{"us" if vols[l]["corpora"] == 1 else "ora"}'
                    f'{" · " + _n(vols[l]["lines"]) + " lines" if vols[l]["lines"] else ""} · GitHub ★ {_n(vols[l]["gh_stars"])}<span class="hs" hidden></span></span></div></a>'
                    for l in order)
    repos = len({w["repo_url"].lower() for pp in people.values() for w in pp["work"].values()})
    corpora = len({c for pp in people.values() for c in pp["corpora"]})
    return f"""<main class="cwrap"><section class="whead"><h1>The people behind the hub</h1>
<p>{len(people):,} developers agreed to let AI agents learn from their work: {repos:,} repositories across {corpora:,} corpora, each included with the author's permission,
under its own licence, with attribution. Sorted by GitHub stars on their repositories; hub stars are the ones visitors give here. Every source is still in licence review; none is live yet unless its card says so.</p>
<a class="cta" href="../contribute.html">Add yours</a></section><div class="wall" data-stars="contributor">{tiles}</div></main>{STARS_JS}"""


def og(html, title, desc, url, image):
    tags = (f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">'
            f'<meta property="og:url" content="{url}"><meta property="og:image" content="{image}">'
            f'<meta name="twitter:card" content="summary"><link rel="canonical" href="{url}">')
    return html.replace("</head>", tags + "</head>", 1)


def by_corpus(people):
    """corpus slug -> logins appearing in it, for the corpus pages' Contributors block."""
    out = {}
    for login, pp in people.items():
        for slug in pp["corpora"]:
            out.setdefault(slug, []).append(login)
    return {k: sorted(v, key=str.lower) for k, v in out.items()}


def corpus_section(logins, esc, people):
    """The Contributors block on /corpus/<slug>.html (empty when nobody is listed)."""
    if not logins:
        return ""
    tiles = "".join(f'<a href="../contributors/{esc(l)}.html"><img src="https://github.com/{esc(l)}.png?size=88" alt="" loading="lazy">'
                    f'<div><b>{esc(people[l]["name"] or l)}</b><span>@{esc(l)}</span></div></a>' for l in logins)
    return (f'<section class="detail" id="contributors"><h2>Contributors ({len(logins)})</h2>'
            f'<p class="note">People whose work this corpus selects or pins, each with their permission. '
            f'<a href="../contributors/index.html">All contributors</a>.</p><div class="wall">{tiles}</div></section>')


def generate(out, hub_dir, page, esc, live_slugs, registry=None, people=None):
    if people is None:
        people = load(hub_dir, registry)
    if not people:
        return 0
    pages = {c["slug"] for c in registry or []}
    d = pathlib.Path(out) / "contributors"
    d.mkdir(exist_ok=True)
    for login, pp in people.items():
        name = pp["name"] or login
        first = sorted(pp["work"].values(), key=lambda w: -(w.get("repo_stars") or 0))[0]
        title = f"{name} (@{login}): XERJ Corpus Hub contributor"
        desc = f"{name}'s work in {first['repo']} is in the XERJ Corpus Hub, the reference memory AI coding agents search before writing code."
        html = page(title, desc, person_body(pp, esc, live_slugs, pages), rel="../")
        (d / f"{login}.html").write_text(og(html, esc(title), esc(desc), f"{SITE}/contributors/{login}.html", f"https://github.com/{login}.png?size=400"))
        (d / login).mkdir(exist_ok=True)
        (d / login / "badge.svg").write_text(badge_svg())
    (d / "stars-targets.json").write_text(json.dumps(stars_targets(people, registry), separators=(",", ":")))
    html = page("Contributors: XERJ Corpus Hub", "The developers whose work AI agents retrieve from the XERJ Corpus Hub", wall_body(people, esc, live_slugs), rel="../")
    (d / "index.html").write_text(og(html, "The people behind the XERJ Corpus Hub", "Developers who agreed to let AI agents learn from their work",
                                     f"{SITE}/contributors/", "https://github.com/xerj-org.png"))
    return len(people)
