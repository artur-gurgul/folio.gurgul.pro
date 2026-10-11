#!/usr/bin/env python3
"""cache-bust.py — give every file a page loads a URL that changes when the file does: ?v=<its content hash>.

WHY. GitHub Pages sends `Cache-Control: max-age=600` for every file, and a site cannot change
that. After a release, a browser that had the site in the last ten minutes reloads the page
(a reload asks again for the page itself) but takes its stylesheets, scripts and figures from
its cache: new HTML on old CSS. On 2026-10-10 that showed the new dark figures on the old white
figure card, worse than either. Asked for (2026-10-11): versioned CSS, JS and figure URLs, so a
deploy never mixes. With a ?v= that changes with the file's bytes, a new page names URLs no cache
holds yet; an unchanged file keeps its URL and stays cached.

WHAT IS STAMPED — the local files a page loads:
  <link href> · <script src> · <img src>   the stylesheets, the icon, the preloads, the scripts,
                                           the figures and the print SVG
  data-nav · data-index · data-search      the JSON files site.js and memos.js fetch (the
                                           nav.json preload in <head> gets the same URL, so the
                                           preloaded response is the one that is used)
NOT stamped:
  fonts (.woff2 …)   a font's preload must be the SAME URL as the @font-face in all.css, which
                     this does not rewrite; stamping only the preload downloads each font twice.
                     The fonts are pinned files (FONTS.md) and do not change.
  <a href>           a link (the PDF, the print view, another page) is opened, not loaded by the
                     page, and its URL is one people copy and share.
  other URLs         absolute ones (not ours), and any with a query other than v=.

The value is the first 10 hex digits of the SHA-256 of the file as published (the file in the
directory given). GitHub Pages ignores the query and serves the file; the query is only the
cache's key.

Run it LAST, on the directory that is published: tools/build.py runs it on the build. Run it
again after anything replaces a file the pages load: the maintainer's release flow puts back the
published figures of folios a change did not touch. A second run changes nothing.

USAGE
  python3 tools/cache-bust.py docs             # stamp every page under docs/
  python3 tools/cache-bust.py docs --check     # change nothing; exit 1 if a stamp is missing,
                                               #   stale, or names a file that is not there
  python3 tools/cache-bust.py --selftest       # prove the stamping and the check can go red

Standard library only.

EXIT: 0 done / passed · 1 --check failed, or a page names a file that is not there · 2 could not run
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

# the attributes that make a page LOAD a file, by tag; and the ones naming a JSON file a script
# fetches, on whatever element carries them
LOADED = {"link": ("href",), "script": ("src",), "img": ("src",)}
FETCHED = ("data-nav", "data-index", "data-search")
FONTS = {".woff2", ".woff", ".ttf", ".otf", ".eot"}
HASH_LEN = 10
VERSION = re.compile(rf"^v=[0-9a-f]{{{HASH_LEN}}}$")
ATTR = re.compile(r'(?<=\s)(?P<key>[A-Za-z][\w:.-]*)=(?P<q>["\'])(?P<url>.*?)(?P=q)', re.S)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class StartTags(HTMLParser):
    """Every start tag of a page, as (line, column, tag, its raw text). An HTML parser, not a
    regular expression over the page: an attribute value may hold a '>' or a '<'."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[int, int, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        raw = self.get_starttag_text()
        if raw:
            self.found.append((*self.getpos(), tag, raw))


def digest(path: Path, cache: dict[Path, str]) -> str:
    if path not in cache:
        cache[path] = hashlib.sha256(path.read_bytes()).hexdigest()[:HASH_LEN]
    return cache[path]


def target(url: str, page: Path, root: Path) -> Path | None:
    """The local file a URL names, or None when the URL is not one this stamps."""
    if not url or url.startswith(("#", "//")) or SCHEME.match(url):
        return None
    parts = urlsplit(url)
    if parts.query and not VERSION.match(parts.query):
        return None
    path = unquote(parts.path)
    if not path or Path(path).suffix.lower() in FONTS or path.endswith("/"):
        return None
    return (root / path.lstrip("/")) if path.startswith("/") else (page.parent / path)


def stamped(url: str, file: Path, root: Path, cache: dict[Path, str]) -> str | None:
    """The URL with ?v=<hash of file>, or None when the file is not in the published tree."""
    try:
        file.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if not file.is_file():
        return None
    return urlsplit(url)._replace(query=f"v={digest(file, cache)}").geturl()


def stamp_page(page: Path, root: Path, cache: dict[Path, str]) -> tuple[str, list[str], int]:
    """(the page with every loaded file stamped, problems, how many URLs it manages)."""
    text = page.read_text(errors="replace")
    parser = StartTags()
    parser.feed(text)
    parser.close()
    starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]
    problems: list[str] = []
    managed = 0
    out, last = [], 0
    for line, col, tag, raw in parser.found:
        at = starts[line - 1] + col
        if text[at:at + len(raw)] != raw:
            raise RuntimeError(f"{page}: lost track of a tag at line {line} (parser and text disagree)")
        keys = LOADED.get(tag, ()) + FETCHED

        def rewrite(m: re.Match) -> str:
            nonlocal managed
            if m.group("key").lower() not in keys:
                return m.group(0)
            url = m.group("url")
            file = target(url, page, root)
            if file is None:
                return m.group(0)
            managed += 1
            new = stamped(url, file, root, cache)
            if new is None:
                problems.append(f"{page.relative_to(root)}: <{tag} {m.group('key')}> names {url}, "
                                f"which is not a file in {root.name}/")
                return m.group(0)
            return f'{m.group("key")}={m.group("q")}{new}{m.group("q")}'

        new_raw = ATTR.sub(rewrite, raw)
        out.append(text[last:at])
        out.append(new_raw)
        last = at + len(raw)
    out.append(text[last:])
    return "".join(out), problems, managed


def pages(root: Path) -> list[Path]:
    return sorted(root.rglob("*.html"))


def run(root: Path, check: bool) -> tuple[list[str], int, int, int]:
    """(problems, pages changed or stale, URLs managed, pages) — with check, nothing is written."""
    cache: dict[Path, str] = {}
    problems: list[str] = []
    changed = managed = 0
    found = pages(root)
    for page in found:
        text = page.read_text(errors="replace")
        new, bad, n = stamp_page(page, root, cache)
        problems += bad
        managed += n
        if new != text:
            changed += 1
            if check:
                problems.append(f"{page.relative_to(root)}: a stamp is missing or stale")
            else:
                page.write_text(new)
    return problems, changed, managed, len(found)


def selftest() -> bool:
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch) / "docs"
        (root / "static" / "css").mkdir(parents=True)
        (root / "static" / "fonts").mkdir(parents=True)
        (root / "area").mkdir()
        css = root / "static" / "css" / "sheet.css"
        css.write_text("body{color:#e8e8e4}")
        (root / "static" / "fonts" / "f.woff2").write_bytes(b"font")
        (root / "nav.json").write_text("{}")
        (root / "area" / "p-fig1.svg").write_text("<svg/>")
        page = root / "area" / "p.html"
        page.write_text(
            '<!DOCTYPE html><html><head>'
            '<link rel="canonical" href="https://example.org/area/p.html">'
            '<link rel="preload" href="/static/fonts/f.woff2" as="font">'
            '<link rel="preload" href="/nav.json" as="fetch" crossorigin>'
            '<link rel="stylesheet" href="/static/css/sheet.css"></head>'
            '<body data-nav="/nav.json">'
            '<img alt="a > b" src="p-fig1.svg" width="10" height="10">'
            '<pre>&lt;img src="p-fig1.svg"&gt;</pre>'
            '<a href="p-fig1.svg">Print view</a></body></html>')
        h_css = hashlib.sha256(css.read_bytes()).hexdigest()[:HASH_LEN]

        results.append(("--check flags a page whose files carry no stamp", bool(run(root, True)[0])))
        problems, changed, managed, _ = run(root, False)
        html = page.read_text()
        results += [
            ("stamping finds the stylesheet, the nav.json preload and data-nav, and the figure",
             not problems and changed == 1 and managed == 4),
            ("the stamp is the file's own SHA-256", f'href="/static/css/sheet.css?v={h_css}"' in html),
            ("the nav.json preload and data-nav get the SAME URL",
             len(set(re.findall(r'"/nav\.json\?v=([0-9a-f]+)"', html))) == 1
             and html.count("/nav.json?v=") == 2),
            ("a figure whose alt holds '>' is stamped", re.search(r'alt="a > b" src="p-fig1\.svg\?v=', html)),
            ("a link (<a href>) is NOT stamped", '<a href="p-fig1.svg">' in html),
            ("a font preload is NOT stamped (it must equal the CSS @font-face URL)",
             'href="/static/fonts/f.woff2"' in html),
            ("an absolute URL is NOT stamped", 'href="https://example.org/area/p.html"' in html),
            ("escaped text that looks like a tag is NOT stamped", '&lt;img src="p-fig1.svg"&gt;' in html),
            ("--check passes the stamped page", not run(root, True)[0]),
            ("a second run changes nothing", run(root, False)[1] == 0 and page.read_text() == html),
        ]
        css.write_text("body{color:#ffffff}")
        results.append(("--check flags a stamp gone stale (the file changed)", bool(run(root, True)[0])))
        run(root, False)
        results.append(("a re-run fixes the stale stamp", not run(root, True)[0]))
        page.write_text(page.read_text().replace("</body>", '<script src="/static/js/gone.js"></script></body>'))
        results.append(("a page naming a file that is not there is a problem", bool(run(root, False)[0])))
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
    return all(bool(ok) for _, ok in results)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="the published directory (docs/, or the build's output)")
    ap.add_argument("--check", action="store_true", help="change nothing; fail if a stamp is missing or stale")
    ap.add_argument("--selftest", action="store_true", help="prove the stamping and the check")
    args = ap.parse_args()

    if args.selftest:
        print("cache-bust self-test")
        ok = selftest()
        print("RESULT: PASS" if ok else "RESULT: FAIL")
        return 0 if ok else 1
    if not args.root or not Path(args.root).is_dir():
        print(f"COULD-NOT-RUN: {args.root!r} is not a directory", file=sys.stderr)
        return 2
    root = Path(args.root)
    if not pages(root):
        print(f"COULD-NOT-RUN: no pages (*.html) under {args.root}", file=sys.stderr)
        return 2
    try:
        problems, changed, managed, n = run(root, args.check)
    except RuntimeError as e:
        print(f"COULD-NOT-RUN: {e}", file=sys.stderr)
        return 2
    for line in problems[:40]:
        print(f"FAIL {line}")
    if len(problems) > 40:
        print(f"FAIL … and {len(problems) - 40} more")
    if args.check:
        print(f"{n - changed}/{n} pages: every file they load carries its hash ({managed} URLs)")
    else:
        print(f"stamped {changed} page(s); {n - changed} already current ({managed} URLs)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
