"""Build-time squarified treemap for /contributors/ (stdlib only, no JS).

Each tile's area is proportional to the contributor's GitHub stars, the same
figure the wall ranks by (contributors.volume()["gh_stars"]). The layout is
computed here, in pixels, for three fixed design widths, and shipped as
absolutely positioned tiles in percentages of an aspect-ratio box. A CSS
container query shows the layout whose design width is the *smallest* width it
is shown at, so tiles only ever grow from the size they were checked at.

Readability rule: every tile, the smallest included, fits its label on one
line at 14px or more (estimated with a deliberately wide glyph width). The
map shows the top K contributors for the largest K at which that holds, with
areas proportional among those K; everyone below the cut is not squeezed in
but stays in the full list under the map (the caption says how many).

"Squarified" here is Bruls/Huizing/van Wijk's algorithm run in a space
stretched by ASPECT, so it optimises tiles toward ASPECT:1 (wide) rather than
1:1: a one-line name needs a wide tile, and the same area as a wide tile fits
a longer name than as a square.
"""

GAP = 2                 # px between tiles (each tile is inset by GAP)
PAD_X = 8               # horizontal padding inside a tile, each side
MIN_FONT = 14           # px: the smallest name on any tile
LINE = 1.25             # line-height of tile text
GLYPH = 0.62            # em per character; wider than IBM Plex Sans 600 averages (~0.55)
PAD_Y = 6               # vertical padding inside a tile, each side
BORDER = 1
CHROME = 2 * (PAD_Y + BORDER)                      # vertical px a tile spends on padding + border
MIN_H = int(MIN_FONT * LINE + CHROME + 0.999) + 1  # one 14px line, rounded up, +1px slack
INLINE_AV, INLINE_GAP = 32, 8                      # avatar beside the two-line label

# (name, design width px, design height px, target tile aspect, container width range it serves)
LAYOUTS = (
    ("l", 1040, 720, 2.5, "(min-width:1040px)"),
    ("m", 680, 620, 3.0, "(min-width:680px) and (max-width:1039.98px)"),
    ("s", 320, 540, 3.0, "(max-width:679.98px)"),
)

# Light tints; --z-ink #1a1a1a and --z-mute #4a4843 are both >= 7:1 on each
# (WCAG AAA for normal text). test_gen.TreemapTest checks the ratios.
TINTS = ("#fff1c7", "#ebe4f7", "#dfebf5", "#e2f0e4", "#f7e6de", "#eeebe3")
INK, MUTE = "#1a1a1a", "#4a4843"


def text_w(s, px):
    return len(s) * px * GLYPH + 2 * PAD_X


def _worst(row, short):
    s = sum(row)
    return max(max(row) * short * short / (s * s), (s * s) / (short * short * min(row)))


def squarify(values, w, h, aspect=1.0):
    """squarify() toward tiles of `aspect`:1 (width:height): lay out in a space
    narrowed by `aspect`, then stretch x back. Areas are unchanged."""
    return [(x * aspect, y, rw * aspect, rh) for x, y, rw, rh in _squarify(values, w / aspect, h)]


def _squarify(values, w, h):
    """Bruls/Huizing/van Wijk squarified layout of `values` (sorted descending,
    all > 0) into a w x h rectangle. Returns [(x, y, w, h)] in input order."""
    total = float(sum(values))
    sizes = [v * w * h / total for v in values]
    out, x, y = [], 0.0, 0.0
    i = 0
    while i < len(sizes):
        short = min(w, h)
        row = [sizes[i]]
        j = i + 1
        while j < len(sizes) and _worst(row + [sizes[j]], short) <= _worst(row, short):
            row.append(sizes[j])
            j += 1
        s = sum(row)
        if w >= h:                      # vertical strip on the left
            rw = s / h if h else 0
            yy = y
            for a in row:
                rh = a / rw if rw else 0
                out.append((x, yy, rw, rh))
                yy += rh
            x += rw
            w -= rw
        else:                           # horizontal strip on top
            rh = s / w if w else 0
            xx = x
            for a in row:
                rw_ = a / rh if rh else 0
                out.append((xx, y, rw_, rh))
                xx += rw_
            y += rh
            h -= rh
        i = j
    return out


def _label(item, w, h):
    """Choose what a w x h tile (already inset by GAP) shows, or None if not
    even the shortest label fits one 14px line. Widths include the side
    padding and border (text_w); heights include CHROME and the 2px gaps."""
    if h < MIN_H:
        return None
    names = [item["name"], item["login"]] if item["name"] != item["login"] else [item["login"]]
    stars = item["stars_txt"]
    star_h = 14 * LINE
    if w >= 150 and h >= 132:          # big: avatar + name + stars
        av = int(max(40, min(104, min(w, h) * 0.42)))
        for fs in (20, 18, 16):
            for nm in names:
                if text_w(nm, fs) <= w and text_w(stars, 14) <= w and av + 2 + fs * LINE + 2 + star_h + CHROME + 1 <= h:
                    return {"tier": "xl", "text": nm, "fs": fs, "av": av}
    for fs in (16, 14):                 # two lines: name + stars, a small avatar beside them if it fits
        if fs * LINE + 2 + star_h + CHROME + 1 <= h and text_w(stars, 14) <= w:
            for nm in names:
                if text_w(nm, fs) <= w:
                    room = w - max(text_w(nm, fs), text_w(stars, 14))
                    return {"tier": "m", "text": nm, "fs": fs, "av": INLINE_AV if room >= INLINE_AV + INLINE_GAP else 0}
    for nm in names:                    # one line: name only (stars in the tooltip)
        if text_w(nm, MIN_FONT) <= w:
            return {"tier": "s", "text": nm, "fs": MIN_FONT}
    return None


def fit(items, w, h, aspect=1.0, cap=300):
    """items: [{"login","name","stars","stars_txt"}] sorted by stars desc.
    Returns [(item, (x,y,w,h), label)] for the top K items with stars > 0,
    for the largest K (<= cap) at which every tile's label fits."""
    pos = [it for it in items if it["stars"] > 0]
    for k in range(min(len(pos), cap), 0, -1):
        top = pos[:k]
        rects = squarify([it["stars"] for it in top], w, h, aspect)
        labels = [_label(it, r[2] - GAP, r[3] - GAP) for it, r in zip(top, rects)]
        if all(labels):
            return list(zip(top, rects, labels))
    return []


def _pct(v, total):
    return f"{100.0 * v / total:.4f}".rstrip("0").rstrip(".") + "%"


def render(items, esc, href, caption=lambda n: ""):
    """HTML for the three layouts and how many each shows. `href(login)` gives
    each tile's link."""
    parts, shown = [], {}
    for key, W, H, aspect, _ in LAYOUTS:
        tiles = fit(items, W, H, aspect)
        shown[key] = len(tiles)
        lis = []
        for idx, (it, (x, y, w, h), lab) in enumerate(tiles):
            style = (f"left:{_pct(x, W)};top:{_pct(y, H)};width:calc({_pct(w, W)} - {GAP}px);"
                     f"height:calc({_pct(h, H)} - {GAP}px);background:{TINTS[idx % len(TINTS)]}")
            full = f'{it["name"]} (@{it["login"]}), {it["stars"]:,} GitHub stars'
            av, cls = "", f't-{lab["tier"]}'
            if lab.get("av"):
                a = lab["av"]
                cls += " av" if lab["tier"] == "m" else ""
                av = (f'<img src="https://github.com/{esc(it["login"])}.png?size={a * 2}" width="{a}" height="{a}" '
                      f'alt="" loading="lazy" decoding="async">')
            stars = f'<span>{esc(it["stars_txt"])}</span>' if lab["tier"] in ("xl", "m") else ""
            lis.append(f'<li class="{cls}" style="{style}"><a href="{esc(href(it["login"]))}" '
                       f'title="{esc(full)}" aria-label="{esc(full)}">{av}<b style="font-size:{lab["fs"]}px">{esc(lab["text"])}</b>{stars}</a></li>')
        parts.append(f'<div class="tm tm-{key}" data-shown="{len(tiles)}"><ol class="tmap" style="aspect-ratio:{W}/{H}">'
                     f'{"".join(lis)}</ol>{caption(len(tiles))}</div>')
    return "".join(parts), shown


STYLE = (
    "/* contributors treemap (treemap.py): build-time squarified layout */\n"
    ".tmwrap{container-type:inline-size;margin:var(--sp-6) 0 var(--sp-4)}\n"
    ".tm{display:none}\n"
    ".tmap{position:relative;list-style:none;margin:0;padding:0;width:100%}\n"
    + "".join(f"@container {q}{{.tm-{k}{{display:block}}}}\n" for k, _, _, _, q in LAYOUTS)
    + f".tmap li{{position:absolute;overflow:hidden;border:{BORDER}px solid rgba(26,26,26,.14)}}\n"
    ".tmap a{display:flex;flex-direction:column;justify-content:center;gap:2px;width:100%;height:100%;"
    f"padding:{PAD_Y}px {PAD_X - BORDER}px;text-decoration:none;color:{INK};line-height:{LINE};font-family:var(--font-data)}}\n"
    ".tmap a:hover,.tmap a:focus-visible{background:rgba(255,255,255,.55);outline:2px solid var(--z-ink);outline-offset:-2px}\n"
    ".tmap b{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}\n"
    f".tmap span{{display:block;font-size:14px;color:{MUTE};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}}\n"
    ".tmap .t-xl a{justify-content:flex-end}\n"
    ".tmap img{display:block;border-radius:50%;border:1px solid rgba(26,26,26,.18);background:#fff;margin-bottom:auto}\n"
    f".tmap .av a{{display:grid;grid-template-columns:{INLINE_AV}px minmax(0,1fr);column-gap:{INLINE_GAP}px;row-gap:2px;align-content:center}}\n"
    ".tmap .av img{grid-row:1 / span 2;align-self:center;margin:0}\n"
    ".tmcap{font-size:var(--fs-13);color:var(--z-mute);margin:var(--sp-2) 0 0}\n"
)
