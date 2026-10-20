"""Contributor pages for hub.xerj.org: one GitHub-profile-style page per author
who agreed to contribute, a wall of all of them, and a README badge each.

Sources: tools/xerj-code/hub/candidates/authors/CONTRIBUTORS.jsonl (written by
the outreach pipeline; one row per approved contribution), the themed candidate
corpora's CONTRIBUTORS-2026-10.md, and the registry manifests. A person is one
login however many corpora they appear in (see load()). Every number on a
page is read from those files; a number we do not have is left off the page,
never estimated. There is no per-author retrieval counter yet (nothing here is
live), so the pages show no retrieval figure at all rather than a placeholder.

  out/contributors/index.html          the wall: star treemap + first chunk of the list
  out/contributors/list.<n>.json       the rest of the list, CHUNK rows a file (infinite scroll)
  out/contributors/list.<n>.html       the same chunks as plain HTML pages (crawlable fallback)
  out/contributors/<login>.html        one author (or one upstream owner, see upstream())
  out/contributors/<login>/badge.svg   "XERJ Corpus Hub | contributor" badge
  out/corpus/<slug>.html               candidate corpora (author / themed) that have no
                                       registry page yet, so every contributor's corpus links
"""
import json, pathlib, re, urllib.parse, collections
import treemap

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
.wall img{width:44px;height:44px;border-radius:50%;flex:none}
.wall div{min-width:0}.wall b,.wall span{overflow-wrap:anywhere}
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
.whead h2,.wallh{font-family:var(--font-display);font-weight:800;font-size:var(--fs-32);line-height:1.1;margin:var(--sp-10) 0 0}
.wallmore{margin:var(--sp-6) 0;color:var(--z-mute);font-size:var(--fs-13)}
.wallmore button,.pager a{font-family:var(--font-data);font-size:var(--fs-13);font-weight:600;text-decoration:none;color:var(--z-ink);
border:1px solid var(--z-ink);background:#fff;padding:.5em 1em;cursor:pointer;margin-left:var(--sp-3)}
.wallmore button[hidden],.pager[hidden]{display:none}
.pager{display:flex;flex-wrap:wrap;gap:var(--sp-2);align-items:center;margin:var(--sp-6) 0}
.pager a{margin:0;min-width:44px;text-align:center}.pager a[aria-current]{background:var(--z-ink);color:#fff}
.people h3{font-family:var(--font-data);font-size:var(--fs-20);margin:var(--sp-6) 0 var(--sp-2)}
.chip.up{color:var(--z-cmp);border-color:var(--z-cmp)}
@media (max-width:820px){.prof{grid-template-columns:1fr}.prof .av{width:140px;height:140px}.kpi{flex-basis:40%}.whead h1{font-size:var(--fs-56)}}
@media (max-width:420px){.whead h1{font-size:44px}.wall{grid-template-columns:1fr}}
""" + treemap.STYLE

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
  // hub-star counts on the wall; hubStarMark() is called again by WALL_JS for
  // every chunk it appends, and skips tiles it has already marked
  var counts=null,wall=document.querySelector('.wall[data-stars]');
  window.hubStarMark=function(root){if(!counts||!root)return;
    root.querySelectorAll('[data-id]').forEach(function(a){var s=a.querySelector('.hs');if(!s||!s.hidden)return;
      s.textContent=' · hub ★ '+fmt(counts[a.dataset.id]||0);s.hidden=false})};
  if(wall)fetch(API+'?kind='+wall.dataset.stars).then(function(r){return r.json()}).then(function(r){
    if(!r||!r.ok||!r.enabled)return;
    counts=r.counts||{};window.hubStarMark(wall);
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


CHUNK = 500            # list rows per JSON chunk / plain-HTML page


def wall_order(people, vols):
    """The wall's order: GitHub stars on the contributor's repos, then login."""
    return sorted(people, key=lambda l: (-vols[l]["gh_stars"], l.lower()))


def wall_tile(l, pp, v, esc):
    return (f'<a href="{esc(l)}.html" data-id="{esc(l.lower())}"><img src="https://github.com/{esc(l)}.png?size=88" alt="" loading="lazy" width="44" height="44">'
            f'<div><b>{esc(pp["name"] or l)}</b><span>@{esc(l)} · {v["corpora"]} corp{"us" if v["corpora"] == 1 else "ora"}'
            f'{" · " + _n(v["lines"]) + " lines" if v["lines"] else ""} · GitHub ★ {_n(v["gh_stars"])}<span class="hs" hidden></span></span></div></a>')


def wall_row(l, pp, v):
    """One list row in list.<n>.json; WALL_JS renders it exactly like wall_tile()."""
    return [l, pp["name"] if pp["name"] and pp["name"] != l else "", v["corpora"], v["lines"] or 0, v["gh_stars"]]


def pager(n_pages, current):
    links = " ".join(f'<a href="{"index.html" if i == 1 else f"list.{i}.html"}"{" aria-current=page" if i == current else ""}>{i}</a>'
                     for i in range(1, n_pages + 1))
    return f'<nav class="pager" aria-label="All contributors, page by page"><b>Pages</b> {links}</nav>'


# Infinite scroll for the wall: the first CHUNK rows are in the HTML; the rest
# come from list.<n>.json as the "Showing" line nears the viewport (or on the
# button). The plain pager (list.<n>.html) stays in the HTML for crawlers and
# no-JS readers; this script hides it, and shows it again if a chunk fails.
WALL_JS = """<script>
(function(){
  var wall=document.querySelector('.wall[data-chunks]');if(!wall)return;
  var next=2,last=+wall.dataset.chunks,total=+wall.dataset.total,busy=false,io=null;
  var more=document.getElementById('wallmore'),btn=more.querySelector('button'),st=more.querySelector('[data-st]');
  var pg=document.querySelector('nav.pager');if(pg&&last>1)pg.hidden=true;
  function fmt(n){return Number(n).toLocaleString('en-US')}
  function el(t,a,txt){var e=document.createElement(t);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e}
  function tile(r){var l=r[0],a=el('a',{href:l+'.html','data-id':l.toLowerCase()});
    a.appendChild(el('img',{src:'https://github.com/'+encodeURIComponent(l)+'.png?size=88',alt:'',loading:'lazy',width:'44',height:'44'}));
    var d=el('div');d.appendChild(el('b',{},r[1]||l));
    var s=el('span',{},'@'+l+' · '+r[2]+' corp'+(r[2]===1?'us':'ora')+(r[3]?' · '+fmt(r[3])+' lines':'')+' · GitHub ★ '+fmt(r[4]));
    var hs=el('span',{'class':'hs'});hs.hidden=true;s.appendChild(hs);d.appendChild(s);a.appendChild(d);return a}
  function done(){st.textContent='Showing '+fmt(wall.children.length)+' of '+fmt(total)+'.';
    if(next>last){btn.hidden=true;if(io)io.disconnect();return}
    if(io&&more.getBoundingClientRect().top<innerHeight+800)setTimeout(load,50)}
  function load(){if(busy||next>last)return;busy=true;btn.disabled=true;
    fetch('/contributors/list.'+next+'.json').then(function(r){if(!r.ok)throw r.status;return r.json()}).then(function(rows){
      var f=document.createDocumentFragment();rows.forEach(function(r){f.appendChild(tile(r))});wall.appendChild(f);next++;
      if(window.hubStarMark)window.hubStarMark(wall);busy=false;btn.disabled=false;done()
    }).catch(function(){busy=false;btn.disabled=false;if(pg)pg.hidden=false;st.textContent='Could not load more here; use the pages below.'})}
  if(last<2){done();return}
  btn.hidden=false;btn.addEventListener('click',load);
  if('IntersectionObserver' in window){io=new IntersectionObserver(function(e){if(e[0].isIntersecting)load()},{rootMargin:'0px 0px 800px 0px'});io.observe(more)}
  done();
})();
</script>"""


def wall_body(people, esc, live_slugs=()):
    vols = {l: volume(pp, live_slugs) for l, pp in people.items()}
    order = wall_order(people, vols)
    n_pages = max(1, -(-len(order) // CHUNK))
    first = "".join(wall_tile(l, people[l], vols[l], esc) for l in order[:CHUNK])
    items = [{"login": l, "name": people[l]["name"] or l, "stars": vols[l]["gh_stars"],
              "stars_txt": "★ " + _n(vols[l]["gh_stars"])} for l in order]
    cap = lambda k: (f'<p class="tmcap">Each tile\'s area is proportional to the GitHub stars on that contributor\'s repositories '
                     f'(the figure the list is sorted by). The top {k} are on the map; all {len(order):,} are in <a href="#list">the list below</a>.</p>')
    tm, _ = treemap.render(items, esc, lambda l: f"{l}.html", cap)
    repos = len({w["repo_url"].lower() for pp in people.values() for w in pp["work"].values()})
    corpora = len({c for pp in people.values() for c in pp["corpora"]})
    return f"""<main class="cwrap"><section class="whead"><h1>The people behind the hub</h1>
<p>{len(people):,} developers agreed to let AI agents learn from their work: {repos:,} repositories across {corpora:,} corpora, each included with the author's permission,
under its own licence, with attribution. Sorted by GitHub stars on their repositories; hub stars are the ones visitors give here. Every source is still in licence review; none is live yet unless its card says so.</p>
<a class="cta" href="../contribute.html">Add yours</a></section>
<section class="tmwrap" aria-labelledby="tmh"><h2 id="tmh" class="wallh">Top contributors by GitHub stars</h2>{tm}</section>
<h2 id="list" class="wallh">All {len(order):,} contributors</h2>
<div class="wall" data-stars="contributor" data-chunks="{n_pages}" data-total="{len(order)}">{first}</div>
<p class="wallmore" id="wallmore" aria-live="polite"><span data-st>Showing {min(CHUNK, len(order)):,} of {len(order):,}.</span><button type="button" hidden>Load more</button></p>
{pager(n_pages, 1)}</main>{STARS_JS}{WALL_JS}"""


def wall_chunks(people, esc, live_slugs=()):
    """[(n, rows, html_body)] for n = 2.. : list.<n>.json and list.<n>.html."""
    vols = {l: volume(pp, live_slugs) for l, pp in people.items()}
    order = wall_order(people, vols)
    n_pages = max(1, -(-len(order) // CHUNK))
    out = []
    for n in range(2, n_pages + 1):
        part = order[(n - 1) * CHUNK:n * CHUNK]
        tiles = "".join(wall_tile(l, people[l], vols[l], esc) for l in part)
        body = (f'<main class="cwrap"><p><a class="backlink" href="index.html">&larr; the star map and the full list</a></p>'
                f'<section class="whead"><h1>Contributors, page {n} of {n_pages}</h1>'
                f'<p>Contributors {(n - 1) * CHUNK + 1:,} to {(n - 1) * CHUNK + len(part):,} of {len(order):,}, sorted by GitHub stars on their repositories.</p></section>'
                f'<div class="wall" data-stars="contributor">{tiles}</div>{pager(n_pages, n)}</main>{STARS_JS}')
        out.append((n, [wall_row(l, people[l], vols[l]) for l in part], body))
    return out


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


# Corpus pages credit people in three tiers, each linking /contributors/<login>:
#   contributors  signed up (CONTRIBUTORS.jsonl / themed table); work included with permission
#   upstream      the GitHub owner of each pinned repository who has not signed up:
#                 credited under the repository's licence on an attribution page
#   curator       CURATOR, for a corpus with no GitHub-hosted source (or an aggregate
#                 of more than AGGREGATE owners, whose owners are credited per row
#                 under Sources and pins rather than one page each)
CURATOR = "xerj-org"
AGGREGATE = 50
OWNER_URL = re.compile(r"^https?://github\.com/([A-Za-z0-9-]+)/", re.I)


def _owners(c):
    seen = {}
    for src in list(c.get("repos") or []) + list(c.get("sources") or []):
        m = OWNER_URL.match(src.get("url", "") or "")
        if m and LOGIN_RE.match(m.group(1)):
            seen.setdefault(m.group(1).lower(), (m.group(1), src.get("repo") or src.get("slug") or src.get("url", ""), src.get("url", "")))
    return seen


def credits(registry, people):
    """(per_corpus, upstream). per_corpus: slug -> {"contributors", "upstream",
    "curator", "aggregate"}; upstream: lower login -> {"login", "repos": [(slug,
    repo, url)], "curates": [slug]} for every upstream page to generate."""
    lower = {l.lower(): l for l in people}
    inc = by_corpus(people)
    per, up = {}, {}
    for c in registry or []:
        own = _owners(c)
        agg = len(own) if len(own) > AGGREGATE else 0
        ups = []
        if not agg:
            for key, (login, repo, url) in own.items():
                if key in lower:
                    continue
                u = up.setdefault(key, {"login": login, "repos": [], "curates": []})
                u["repos"].append((c["slug"], repo, url))
                ups.append(u["login"])
        contrib = inc.get(c["slug"], [])
        cur = bool(agg) or not (contrib or ups)
        if cur:
            up.setdefault(CURATOR.lower(), {"login": CURATOR, "repos": [], "curates": []})["curates"].append(c["slug"])
        per[c["slug"]] = {"contributors": contrib, "upstream": sorted(set(ups), key=str.lower),
                          "curator": cur, "aggregate": agg}
    return per, up


def _person_tile(login, label, sub, esc, rel):
    return (f'<a href="{rel}contributors/{esc(login)}.html"><img src="https://github.com/{esc(login)}.png?size=88" alt="" loading="lazy" width="44" height="44">'
            f'<div><b>{esc(label)}</b><span>{esc(sub)}</span></div></a>')


def corpus_section(logins, esc, people, upstream=(), curator=False, aggregate=0, rel="../"):
    """The people block on /corpus/<slug>.html (empty when nobody is listed).
    Every tile is avatar + name linking to /contributors/<login>."""
    if not (logins or upstream or curator):
        return ""
    parts = []
    if logins:
        tiles = "".join(_person_tile(l, people[l]["name"] or l, "@" + l, esc, rel) for l in logins)
        parts.append(f'<h3>Contributors ({len(logins)})</h3><p class="note">People whose work this corpus selects or pins, each with their permission.</p>'
                     f'<div class="wall">{tiles}</div>')
    if upstream:
        tiles = "".join(_person_tile(l, l, "@" + l + " · upstream", esc, rel) for l in upstream)
        parts.append(f'<h3>Upstream authors ({len(upstream)})</h3><p class="note">Owners of the pinned repositories, credited under each '
                     f'repository\'s licence. They have not signed up here; their pages are attribution.</p><div class="wall">{tiles}</div>')
    if aggregate:
        parts.append(f'<p class="note">This corpus pins repositories from {aggregate:,} upstream authors; each one is credited with its '
                     f'repository under Sources and pins above.</p>')
    if curator:
        why = ("assembled it from those repositories and reviewed each licence." if aggregate else
               "maintain this registry entry; its sources are not GitHub repositories with an owner to credit, so the "
               "original publishers are the ones listed under Sources and pins.")
        parts.append(f'<h3>Curated by</h3><p class="note">The hub maintainers {why}</p>'
                     f'<div class="wall">{_person_tile(CURATOR, "XERJ Corpus Hub maintainers", "@" + CURATOR + " · curator", esc, rel)}</div>')
    return (f'<section class="detail people" id="contributors"><h2>People behind this corpus</h2>{"".join(parts)}'
            f'<p class="note"><a href="{rel}contributors/index.html">All contributors</a>.</p></section>')


def upstream_body(u, esc, pages):
    login = u["login"]
    cur = login.lower() == CURATOR.lower()
    rows = "".join(f'<li><a href="{esc(url)}">{esc(repo)}</a> in <a href="../corpus/{esc(slug)}.html">corpus {esc(slug)}</a></li>'
                   for slug, repo, url in sorted(u["repos"], key=lambda r: (r[0], r[1])) if slug in pages)
    cura = "".join(f'<li><a href="../corpus/{esc(slug)}.html">{esc(slug)}</a></li>' for slug in sorted(u["curates"]) if slug in pages)
    n = len({r[0] for r in u["repos"]} | set(u["curates"]))
    if cur:
        who = ("The XERJ Corpus Hub maintainers. Besides their own repositories, they curate the registry entries whose sources "
               "have no GitHub owner to credit, and the large aggregate corpora.")
        claim = ""
    else:
        who = (f"@{esc(login)} is credited here because their public repositories are pinned in the corpora below, under each "
               f"repository's own licence. This is an attribution page: @{esc(login)} has not signed up as a Corpus Hub contributor, "
               f"and nothing here says they endorse the hub.")
        issue = urllib.parse.quote(f"Corpus Hub: attribution for @{login}")
        claim = (f'<p class="note">Is this you? <a href="../contribute.html">Add your work</a>, or '
                 f'<a href="https://github.com/xerj-org/xerj/issues/new?title={issue}">ask for a change</a>.</p>')
    sec_rows = f"<h2>Pinned repositories</h2><ul>{rows}</ul>" if rows else ""
    sec_cura = f"<h2>Curated corpora</h2><ul>{cura}</ul>" if cura else ""
    role = "curator" if cur else "upstream author"
    return (f'<main class="cwrap"><section class="prof"><img class="av" src="https://github.com/{esc(login)}.png?size=480" alt="{esc(login)}">'
            f'<div><h1>{esc(login)}</h1><div class="login"><a href="https://github.com/{esc(login)}">@{esc(login)}</a></div>'
            f'<div class="chips"><span class="chip up">{role}</span><span class="chip">{n} corp{"us" if n == 1 else "ora"}</span></div>'
            f'<p>{who}</p>{claim}</div></section>{sec_rows}{sec_cura}'
            f'<p class="note"><a href="index.html">All contributors</a></p></main>')


def candidates(people, registry_slugs, hub_dir):
    """Corpora a contributor appears in that have no registry page (author
    corpora and themed candidate corpora, all in licence review):
    slug -> {"kind", "works": [(login, work)], "repos": manifest repos or []}."""
    out = {}
    for login, pp in people.items():
        for w in pp["work"].values():
            for slug in w["corpora"]:
                if slug in registry_slugs or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", slug):
                    continue
                e = out.setdefault(slug, {"kind": pp["corpora"].get(slug, "candidate corpus"), "works": [], "repos": []})
                e["works"].append((login, w))
    for slug, e in out.items():
        m = pathlib.Path(hub_dir) / "candidates" / f"{slug}.json"
        if m.exists():
            try:
                e["repos"] = json.loads(m.read_text()).get("repos") or []
            except ValueError:
                pass
    return out


def candidate_body(slug, e, esc, people):
    logins = sorted({l for l, _ in e["works"]}, key=str.lower)
    rows = []
    for l, w in sorted(e["works"], key=lambda x: (x[1]["repo"].lower(), x[0].lower())):
        commit = (f'<a href="{esc(w["commit_url"])}">{esc(w["commit"][:10])}</a> {esc(w["title"])}' if w["commit"] else "")
        rows.append(f'<tr><td class="mono"><a href="{esc(w["repo_url"])}">{esc(w["repo"])}</a></td><td><a href="../contributors/{esc(l)}.html">@{esc(l)}</a></td>'
                    f'<td class="mono">{commit}</td><td>{esc(w["spdx"] or "?")}</td></tr>')
    pinned = "".join(f'<tr><td class="mono"><a href="{esc(r.get("url", ""))}">{esc(r.get("repo", ""))}</a></td><td class="mono">{esc((r.get("sha") or "")[:12])}</td>'
                     f'<td>{esc((r.get("review") or {}).get("spdx") or r.get("licence") or "?")}</td></tr>' for r in e["repos"])
    pins = (f'<section class="detail"><h2>Pinned sources ({len(e["repos"])})</h2><table><tr><th>source</th><th>pin</th><th>licence</th></tr>{pinned}</table></section>'
            if pinned else "")
    return (f'<main><p><a class="backlink" href="../contributors/index.html">&larr; all contributors</a></p>'
            f'<h1 class="slug">{esc(slug)}</h1>'
            f'<p class="note">{esc(e["kind"])} · status <b>selected · in licence review</b> · not in the hub registry yet</p>'
            f'<div class="kbox"><b>Not installable yet</b><br>This corpus is a candidate: it is not in the hub registry until its licence review passes, '
            f'so <code>xerj corpus add</code> and <code>xerj ask</code> cannot fetch it. The corpus is each whole repository at its pinned commit.</div>'
            f'<section class="detail"><h2>Selected work ({len(rows)})</h2><table><tr><th>repository</th><th>contributor</th><th>selected commit</th><th>licence</th></tr>'
            f'{"".join(rows)}</table></section>{pins}{corpus_section(logins, esc, people)}</main>')


def generate(out, hub_dir, page, esc, live_slugs, registry=None, people=None, upstream=None):
    if people is None:
        people = load(hub_dir, registry)
    if not people:
        return 0
    reg_slugs = {c["slug"] for c in registry or []}
    cands = candidates(people, reg_slugs, hub_dir)
    pages = reg_slugs | set(cands)
    d = pathlib.Path(out) / "contributors"
    d.mkdir(exist_ok=True)
    (pathlib.Path(out) / "corpus").mkdir(exist_ok=True)
    for login, pp in people.items():
        name = pp["name"] or login
        first = sorted(pp["work"].values(), key=lambda w: -(w.get("repo_stars") or 0))[0]
        title = f"{name} (@{login}): XERJ Corpus Hub contributor"
        desc = f"{name}'s work in {first['repo']} is in the XERJ Corpus Hub, the reference memory AI coding agents search before writing code."
        html = page(title, desc, person_body(pp, esc, live_slugs, pages), rel="../")
        (d / f"{login}.html").write_text(og(html, esc(title), esc(desc), f"{SITE}/contributors/{login}.html", f"https://github.com/{login}.png?size=400"))
        (d / login).mkdir(exist_ok=True)
        (d / login / "badge.svg").write_text(badge_svg())
    # upstream owners and the curator: attribution pages, kept out of search indexes
    if upstream is None:
        upstream = credits(registry, people)[1]
    for u in upstream.values():
        title = f"{u['login']}: credited on the XERJ Corpus Hub"
        desc = f"Corpora on the XERJ Corpus Hub that pin repositories by {u['login']}"
        html = page(title, desc, upstream_body(u, esc, pages), rel="../")
        html = html.replace("</head>", '<meta name="robots" content="noindex,follow"></head>', 1)
        (d / f"{u['login']}.html").write_text(og(html, esc(title), esc(desc), f"{SITE}/contributors/{u['login']}.html", f"https://github.com/{u['login']}.png?size=400"))
    # candidate corpora: one page each, so every contributor's corpus chip links somewhere
    for slug, e in cands.items():
        html = page(f"{slug}: candidate corpus, XERJ Corpus Hub", f"Candidate corpus {slug}: selected work in licence review",
                    candidate_body(slug, e, esc, people), rel="../")
        (pathlib.Path(out) / "corpus" / f"{slug}.html").write_text(html)
    (d / "stars-targets.json").write_text(json.dumps(stars_targets(people, registry), separators=(",", ":")))
    html = page("Contributors: XERJ Corpus Hub", "The developers whose work AI agents retrieve from the XERJ Corpus Hub", wall_body(people, esc, live_slugs), rel="../")
    (d / "index.html").write_text(og(html, "The people behind the XERJ Corpus Hub", "Developers who agreed to let AI agents learn from their work",
                                     f"{SITE}/contributors/", "https://github.com/xerj-org.png"))
    for n, rows, body in wall_chunks(people, esc, live_slugs):
        (d / f"list.{n}.json").write_text(json.dumps(rows, separators=(",", ":"), ensure_ascii=False))
        html = page(f"Contributors, page {n}: XERJ Corpus Hub", "The developers whose work AI agents retrieve from the XERJ Corpus Hub", body, rel="../")
        (d / f"list.{n}.html").write_text(og(html, f"Contributors, page {n}: XERJ Corpus Hub", "Developers who agreed to let AI agents learn from their work",
                                             f"{SITE}/contributors/list.{n}.html", "https://github.com/xerj-org.png"))
    return len(people)
