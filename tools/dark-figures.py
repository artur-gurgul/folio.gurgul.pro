#!/usr/bin/env python3
"""dark-figures.py — recolour folio figures for the dark page: the page's own background, the paper's colours shifted for dark.

WHY. The site is dark (page #24292b, text #e8e8e4), but a folio's figures are drawn for paper:
dark ink, light tints, no background of their own. Asked for (2026-10-10): "make script that
modifies colors in svg and put the same background and adjust colors, to be looking nice for the
darker background". So every colour in a figure is moved to its dark-page equivalent:

  white                    → the page's background, exactly: a white box becomes the page
  black                    → the page's text colour, exactly
  the paper's Tango shades → the light shades of the same families — the site's own accents, so
                             blue is still the keyword and green the string (paper #204a87 →
                             screen #729fcf, and so on; PALETTE below)
  every other colour       → its lightness turned over between the page's text and background
  (tints, greys, mixes)      in OKLab (light becomes dark, dark becomes light), its hue kept; a
                             light tint keeps a little more colour, so a box stays visible

Colours are found in fill / stroke / stop-color values (attributes or style), written as
rgb(…%) — what pdftocairo writes — #hex, or white/black. Only FIGURES are recoloured:
<name>-figN.svg. A folio's whole-page <name>.svg is what PRINTS, and paper stays paper.

A recoloured file carries data-folio-dark="1" on its <svg> and is never recoloured twice, so the
script can run after every build and after published files are restored.

USAGE
  python3 tools/dark-figures.py docs              # recolour every figure under docs/
  python3 tools/dark-figures.py docs --check      # exit 1 if a figure is still paper, or its
                                                  #   text colour is under 4.5:1 on the page
  python3 tools/dark-figures.py docs --palette    # the colours the figures use, most used first
  python3 tools/dark-figures.py --selftest        # prove the mapping and the check can go red

Standard library only.

EXIT: 0 done / passed · 1 --check failed · 2 could not run
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

BG = "#24292b"      # the page (all.css --bg)
TEXT = "#e8e8e4"    # the page's text (all.css --text)
MARK = 'data-folio-dark="1"'
FIGURE = re.compile(r"-fig\d+\.svg$")

# the paper's Tango shades (printup-sheet.sty) → the site's light shades (sheet.css --c-*)
PALETTE = {
    (32, 74, 135): "#729fcf",    # sheetBlue = tangoKeyword
    (78, 154, 6): "#8ae234",     # sheetGreen = tangoString
    (143, 89, 2): "#e9b96e",     # sheetBrown = tangoComment
    (206, 92, 0): "#fcaf3e",     # sheetOrange = tangoOperator
    (181, 37, 28): "#ef6b6b",    # sheetRed = BrickRed
}

# Paper has two kinds of colour: INK (text, lines, saturated colours — OKLab lightness up to
# ~0.75) and FILL (pale tints and white, above it). A straight flip of lightness left mid-tones
# where they were — the paper's grey #737373 came out #747777, ~3:1 on the dark page, too faint
# for a label (measured with --palette, 2026-10-10). So ink goes to the LIGHT part of the page's
# range and fills to the DARK part, white landing exactly on the background.
INK_UP_TO = 0.75     # OKLab lightness where ink ends and fill begins
INK_DARKEST = 0.70   # what the palest ink becomes (black becomes the text colour)

VALUE = re.compile(
    r"(?P<key>(?:fill|stroke|stop-color|flood-color)\s*(?:=\s*\"|:\s*))"
    r"(?P<colour>rgb\(\s*[\d.]+%?\s*,\s*[\d.]+%?\s*,\s*[\d.]+%?\s*\)|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|white|black)",
)
GLYPH_FILL = re.compile(r'<g fill="(#[0-9a-fA-F]{6})"[^>]*>\s*<use [^>]*href="#glyph')
SHAPE_FILL = re.compile(r'<path\b[^>]*\sfill="(#[0-9a-fA-F]{6})"')


# ── colour maths: sRGB ↔ OKLab (Björn Ottosson, 2020) ──────────────────────

def parse(colour: str) -> tuple[float, float, float]:
    """A colour value → (r, g, b) in 0..1."""
    c = colour.strip().lower()
    if c == "white":
        return 1.0, 1.0, 1.0
    if c == "black":
        return 0.0, 0.0, 0.0
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    parts = [p.strip() for p in c[c.index("(") + 1:c.rindex(")")].split(",")]
    return tuple(float(p[:-1]) / 100 if p.endswith("%") else float(p) / 255 for p in parts)


def hexed(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, v)) * 255):02x}" for v in rgb)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def to_oklab(rgb):
    r, g, b = (_lin(v) for v in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _from_oklab_linear(L, a, b):
    l, m, s = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, \
              (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
              (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def from_oklch(L, C, h):
    """OKLCh → sRGB, reducing chroma (never lightness or hue) until the colour fits the gamut."""
    lo, hi = 0.0, C
    for _ in range(24):
        lin = _from_oklab_linear(L, hi * math.cos(h), hi * math.sin(h))
        if all(-1e-6 <= v <= 1 + 1e-6 for v in lin):
            return tuple(_gam(min(1.0, max(0.0, v))) for v in lin)
        hi, lo = (lo + hi) / 2, lo
    lin = _from_oklab_linear(L, 0.0, 0.0)
    return tuple(_gam(min(1.0, max(0.0, v))) for v in lin)


def luminance(rgb) -> float:
    r, g, b = (_lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(x, y) -> float:
    a, b = sorted((luminance(x), luminance(y)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# ── the mapping ────────────────────────────────────────────────────────────

L_BG, A_BG, B_BG = to_oklab(parse(BG))
L_TX, A_TX, B_TX = to_oklab(parse(TEXT))


def flip(L: float) -> float:
    """Paper lightness → page lightness: ink into [INK_DARKEST … text], fill into [background …
    INK_DARKEST]; black → the text, white → the background."""
    if L <= INK_UP_TO:
        return L_TX + (INK_DARKEST - L_TX) * (L / INK_UP_TO)
    return INK_DARKEST + (L_BG - INK_DARKEST) * ((L - INK_UP_TO) / (1 - INK_UP_TO))


def recolour(colour: str) -> str:
    rgb = parse(colour)
    key = tuple(round(v * 255) for v in rgb)
    for paper, screen in PALETTE.items():
        if max(abs(k - p) for k, p in zip(key, paper)) <= 2:
            return screen
    L, a, b = to_oklab(rgb)
    C = math.hypot(a, b)
    L2 = flip(min(1.0, max(0.0, L)))
    if C < 0.02:
        # a neutral (white, black, a grey): onto the line from the page's text to its background,
        # so white is the background and black the text EXACTLY, and greys share their tint
        t = (L_TX - L2) / (L_TX - L_BG)
        return hexed(from_oklab_point(L2, A_TX + (A_BG - A_TX) * t, B_TX + (B_BG - B_TX) * t))
    if L > 0.85:
        C = min(C * 1.6, 0.09)             # a pale tint: keep enough colour to see the box
    return hexed(from_oklch(L2, C, math.atan2(b, a)))


def from_oklab_point(L, a, b):
    return from_oklch(L, math.hypot(a, b), math.atan2(b, a))


def lighten_for(colour: str, text_colour: str, need: float = 4.6) -> str:
    """The same hue and chroma, lighter, until `text_colour` reads on it at `need`:1."""
    L, a, b = to_oklab(parse(colour))
    C, h = math.hypot(a, b), math.atan2(b, a)
    rgb = parse(colour)
    while contrast(rgb, parse(text_colour)) < need and L < 0.99:
        L += 0.01
        rgb = from_oklch(L, C, h)
    return hexed(rgb)


def recolour_svg(text: str) -> str:
    if MARK in text[:2000]:
        return text
    out = VALUE.sub(lambda m: m.group("key") + recolour(m.group("colour")), text)
    # INVERSE text (white on a coloured shape on paper — a step marker, a labelled bar) is now
    # the page colour on that shape made light. Where the shape did not come out light enough
    # for it — "paused*" on a mid-brown bar read 3.58:1 (2026-10-10) — lighten the shape.
    edits = {}
    for m in GLYPH_FILL.finditer(out):
        if m.group(1).lower() != BG:
            continue
        shapes = [s for s in SHAPE_FILL.finditer(out, 0, m.start()) if s.group(1).lower() != BG]
        if shapes and contrast(parse(BG), parse(shapes[-1].group(1))) < 4.5:
            edits[shapes[-1].start(1)] = (shapes[-1].group(1), lighten_for(shapes[-1].group(1), BG))
    for pos in sorted(edits, reverse=True):
        old, new = edits[pos]
        out = out[:pos] + new + out[pos + len(old):]
    # the page's text colour for anything that relied on SVG's default black fill, and the mark
    return re.sub(r"<svg\b", f'<svg {MARK} fill="{TEXT}"', out, count=1)


def figures(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.svg") if FIGURE.search(p.name))


def check(paths: list[Path], root: Path | None = None) -> list[str]:
    bad = []
    for p in paths:
        name = p.relative_to(root) if root else p
        text = p.read_text(errors="replace")
        if MARK not in text[:2000]:
            bad.append(f"{name}: still drawn for paper (no {MARK})")
            continue
        seen = set()
        for m in GLYPH_FILL.finditer(text):
            colour = m.group(1).lower()
            if colour == BG:
                # INVERSE text — white on a coloured shape on paper (a numbered step marker),
                # now the page colour on that shape made light. Its background is the shape,
                # not the page: the filled shape drawn just before it.
                shapes = [s.group(1).lower() for s in SHAPE_FILL.finditer(text, 0, m.start())]
                under = next((s for s in reversed(shapes) if s != BG), None)
                if under is None:
                    bad.append(f"{name}: text in the page colour with no shape under it")
                elif (colour, under) not in seen and contrast(parse(colour), parse(under)) < 4.5:
                    bad.append(f"{name}: text {colour} on its shape {under} is "
                               f"{contrast(parse(colour), parse(under)):.2f}:1 (under 4.5:1)")
                seen.add((colour, under or ""))
            elif colour not in seen:
                seen.add(colour)
                ratio = contrast(parse(colour), parse(BG))
                if ratio < 4.5:
                    bad.append(f"{name}: text colour {colour} is {ratio:.2f}:1 on the page (under 4.5:1)")
    return bad


def selftest() -> bool:
    paper = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
             '<rect fill="rgb(100%, 100%, 100%)"/>'
             '<g fill="rgb(0%, 0%, 0%)" fill-opacity="1"><use xlink:href="#glyph-0-1" x="1"/></g>'
             '<path stroke="rgb(12.548828%, 29.019165%, 52.938843%)" fill="rgb(93.003845%, 94.320679%, 96.235657%)"/>'
             '<path style="fill:#ffffff;stroke:black"/></svg>')
    dark = recolour_svg(paper)
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        tmp = Path(scratch) / "selftest-fig1.svg"
        tmp.write_text(paper)
        results.append(("--check flags a figure still drawn for paper", bool(check([tmp]))))
        tmp.write_text(dark.replace(f'fill="{TEXT}" fill-opacity', 'fill="#3a3f41" fill-opacity'))
        results.append(("--check flags text under 4.5:1 on the page", bool(check([tmp]))))
        tmp.write_text(dark)
        results.append(("--check passes the recoloured figure", not check([tmp])))
        # a numbered marker: white digit in a blue circle on paper → page-colour digit, light circle
        marker = recolour_svg(
            '<svg><path fill="rgb(12.5%, 28.999329%, 52.89917%)" d="M0 0"/>'
            '<g fill="rgb(100%, 100%, 100%)" fill-opacity="1"><use xlink:href="#glyph-0-1"/></g></svg>')
        tmp.write_text(marker)
        results.append(("--check passes a page-colour digit on its light circle", not check([tmp])))
        tmp.write_text(marker.replace('<path fill="#729fcf" d="M0 0"/>', ""))
        results.append(("--check flags page-colour text with no shape under it", bool(check([tmp]))))
        # a labelled bar whose mid-tone fill comes out too dark for its page-colour label: the
        # real one, "paused*" in android-coroutines-platform (paper #e9b68c → #a2734b, 3.58:1)
        bar = ('<svg><path fill="#e9b68c" d="M0 0"/>'
               '<g fill="rgb(100%, 100%, 100%)" fill-opacity="1"><use xlink:href="#glyph-0-1"/></g></svg>')
        plain = VALUE.sub(lambda m: m.group("key") + recolour(m.group("colour")), bar)
        tmp.write_text(re.sub(r"<svg\b", f"<svg {MARK}", plain, count=1))
        results.append(("--check flags a page-colour label on a too-dark bar", bool(check([tmp]))))
        tmp.write_text(recolour_svg(bar))
        results.append(("the recolouring lightens that bar until its label reads", not check([tmp])))
    results += [
        ("white becomes the page background", f'<rect fill="{BG}"/>' in dark),
        ("black becomes the page text", f'<g fill="{TEXT}" fill-opacity' in dark),
        ("Tango blue becomes the light Tango blue", 'stroke="#729fcf"' in dark),
        ("a pale blue tint becomes a dark blue tint",
         (lambda c: contrast(c, parse(BG)) < 1.6 and c[2] > c[0])(
             parse(re.search(r'stroke="#729fcf" fill="(#[0-9a-f]{6})"', dark).group(1)))),
        ("style colours are recoloured too", f"fill:{BG};stroke:{TEXT}" in dark),
        ("the paper's grey ink is readable on the page (≥ 4.5:1)",
         contrast(parse(recolour("#737373")), parse(BG)) >= 4.5),
        ("the file is marked, and a second run changes nothing", MARK in dark and recolour_svg(dark) == dark),
    ]
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
    return all(ok for _, ok in results)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="a directory: its figures (*-figN.svg) are recoloured")
    ap.add_argument("--check", action="store_true", help="recolour nothing; fail if a figure is not dark")
    ap.add_argument("--palette", action="store_true", help="list the colours the figures use")
    ap.add_argument("--selftest", action="store_true", help="prove the mapping and the check")
    args = ap.parse_args()

    if args.selftest:
        print("dark-figures self-test")
        ok = selftest()
        print("RESULT: PASS" if ok else "RESULT: FAIL")
        return 0 if ok else 1
    if not args.root or not Path(args.root).is_dir():
        print(f"COULD-NOT-RUN: {args.root!r} is not a directory", file=sys.stderr)
        return 2
    paths = figures(Path(args.root))
    if not paths:
        print(f"COULD-NOT-RUN: no figures (*-figN.svg) under {args.root}", file=sys.stderr)
        return 2

    if args.palette:
        counts = Counter(hexed(parse(m.group("colour")))
                         for p in paths for m in VALUE.finditer(p.read_text(errors="replace")))
        for colour, n in counts.most_common(40):
            print(f"{n:7d}  {colour}  →  {recolour(colour)}")
        print(f"{len(counts)} distinct colours in {len(paths)} figures")
        return 0
    if args.check:
        bad = check(paths, Path(args.root))
        for line in bad[:40]:
            print(f"FAIL {line}")
        print(f"{len(paths) - len({b.split(':')[0] for b in bad})}/{len(paths)} figures are dark "
              f"and their text is at least 4.5:1 on the page")
        return 1 if bad else 0

    done = 0
    for p in paths:
        text = p.read_text(errors="replace")
        new = recolour_svg(text)
        if new != text:
            p.write_text(new)
            done += 1
    print(f"recoloured {done} figure(s); {len(paths) - done} already dark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
