#!/usr/bin/env python3
"""Rewrite the primary nav (`<nav class="nav" …>…</nav>`) of landing pages to the
2026-10 information architecture (/workspace notes: new_ia.md, in the PR body).

    python3 scripts/seo/set_nav.py landing/index.html landing/docs/*.html   # named pages
    python3 scripts/seo/set_nav.py --check landing/index.html                # exit 1 if stale

Six primary items (Docs, Corpus Hub, Use cases, Benchmarks, Blog, For agents), then
GitHub, the release tag and the DAY/NIGHT toggle. Case studies, recipes, dashboards,
X and Discord live in the hubs and the footer map. The release tag is carried over
from the page's existing nav, so `landing-constants-guard.sh` keeps one source.

Only the pages you name are touched: pages owned by in-flight PRs keep their nav
until those land, then one run over `landing/**/*.html` unifies the site.
Stdlib only, like the rest of scripts/seo/.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
LANDING = ROOT / "landing"
NAV_RE = re.compile(r'<nav class="nav"[^>]*>.*?</nav>', re.S)
TAG_RE = re.compile(r'<span data-latest-tag>([^<]*)</span>')

ITEMS = [  # (label, href, section prefixes that make it active)
    ("DOCS", "/docs/", ("docs/",)),
    ("CORPUS HUB ↗", "https://hub.xerj.org", ()),
    ("USE CASES", "/use-cases", ("use-cases", "case-studies")),
    ("BENCHMARKS", "/benchmarks/", ("benchmarks/", "demo/")),
    ("BLOG", "/blog/", ("blog/",)),
    ("FOR AGENTS", "/for-agents", ("for-agents", "agent-search/")),
]


def render(rel: str, tag: str) -> str:
    lines = ['<nav class="nav" aria-label="Primary" id="top">',
             '  <a href="/" class="brand" aria-label="XERJ home">XERJ</a>']
    for label, href, prefixes in ITEMS:
        ext = ' rel="external"' if href.startswith("http") else ""
        cur = any(rel.startswith(p) for p in prefixes)
        attrs = ' class="active" aria-current="page"' if cur else ""
        lines.append(f'  <a href="{href}"{ext}{attrs}>{label}</a>')
    lines += [
        '  <span class="spacer"></span>',
        '  <a href="https://github.com/xerj-org/xerj" rel="external">GITHUB ↗</a>',
        '  <a class="nav-dl" href="https://github.com/xerj-org/xerj/releases/latest" rel="external" '
        f'title="Download the latest XERJ release">↓ <span data-latest-tag>{tag}</span></a>',
        '  <span class="theme">',
        '    <button type="button" data-theme="day" class="active">DAY</button>',
        '    <span class="dash">·</span>',
        '    <button type="button" data-theme="night">NIGHT</button>',
        '  </span>',
        '</nav>',
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("files", nargs="+", type=pathlib.Path)
    a = ap.parse_args()
    stale = 0
    for f in a.files:
        f = f.resolve()
        rel = f.relative_to(LANDING).as_posix()
        src = f.read_text()
        m = NAV_RE.search(src)
        if not m:
            print(f"skip  {rel}: no <nav class=\"nav\">", file=sys.stderr)
            continue
        t = TAG_RE.search(m.group(0)) or TAG_RE.search((LANDING / "index.html").read_text())
        tag = t.group(1) if t else "latest"   # pages without a tag take the home page's
        new = src[:m.start()] + render(rel, tag) + src[m.end():]
        if new != src:
            stale += 1
            if a.check:
                print(f"stale {rel}")
            else:
                f.write_text(new)
                print(f"nav   {rel}")
    return 1 if (a.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
