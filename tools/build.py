#!/usr/bin/env python3
"""build.py — build folio: src/ (the sources) → docs/ (what GitHub Pages serves).

The site is generated with Sajt. Pass a compiled Sajt checkout with --sajt
(or set $SAJT). Every `.tex` under src/ is a folio: Sajt renders it to an HTML
page, SVG figures and a one-page PDF; src/index.md is the front page.

What it does:
  1. runs `sajt build` in src/ (output: src/.build/, ignored by git);
  2. replaces the contents of docs/ with that output — keeping docs/CNAME,
     which tells GitHub Pages the custom domain;
  3. writes docs/.nojekyll, so GitHub serves the files exactly as built.

Needs: Node.js, and for .tex pages xelatex + pdftocairo (TeX Live, poppler).

USAGE
  python3 tools/build.py --sajt /path/to/sajt
  SAJT=/path/to/sajt python3 tools/build.py
  python3 tools/build.py --sajt /path/to/sajt --check     # build, do not touch docs/

EXIT: 0 built · 1 the build failed · 2 could not run (missing tool or Sajt)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = SRC / ".build"
DOCS = ROOT / "docs"
KEEP = {"CNAME"}


def fail(msg: str, code: int, fix: str = "") -> int:
    print(f"{'FAILED' if code == 1 else 'COULD-NOT-RUN'}: {msg}", file=sys.stderr)
    if fix:
        print(f"  Fix: {fix}", file=sys.stderr)
    return code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sajt", default=os.environ.get("SAJT", ""), help="compiled Sajt checkout")
    ap.add_argument("--check", action="store_true", help="build only; leave docs/ untouched")
    args = ap.parse_args()

    if not shutil.which("node"):
        return fail("node not found", 2, "install Node.js")
    if not args.sajt:
        return fail("no Sajt checkout given", 2, "pass --sajt PATH or set $SAJT")
    cli = Path(args.sajt).resolve() / "bin" / "sajt"
    if not cli.is_file():
        return fail(f"{cli} not found", 2, "point --sajt at a compiled Sajt checkout")
    if any(SRC.rglob("*.tex")):
        for tool in ("xelatex", "pdftocairo"):
            if not shutil.which(tool):
                return fail(f"{tool} not found (needed for .tex folios)", 2,
                            "install TeX Live (xetex) and poppler-utils")

    if OUT.exists():
        shutil.rmtree(OUT)
    run = subprocess.run(["node", str(cli), "build"], cwd=SRC)
    if run.returncode != 0:
        return fail(f"sajt build exited {run.returncode}", 1)
    if not (OUT / "index.html").is_file():
        return fail(f"{OUT}/index.html was not produced", 1)
    pages = sorted(p.relative_to(OUT) for p in OUT.rglob("*.html"))
    print(f"built {len(pages)} page(s): {', '.join(map(str, pages))}")

    # The promise of a folio is ONE A4 sheet. A folio whose PDF runs to a
    # second page has broken it, however good the web page looks — fail.
    pdfs = sorted(OUT.rglob("*.pdf"))
    if pdfs and not shutil.which("pdfinfo"):
        return fail("pdfinfo not found (needed to check one page per folio)", 2,
                    "install poppler-utils")
    over = []
    for pdf in pdfs:
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
        n = next((ln.split()[-1] for ln in info.stdout.splitlines() if ln.startswith("Pages:")), "?")
        if n != "1":
            over.append(f"{pdf.relative_to(OUT)} has {n} pages")
    if over:
        return fail("a folio must fit ONE page:\n  " + "\n  ".join(over), 1)
    print(f"one page each: {len(pdfs)} folio PDF(s)")
    if args.check:
        print("check only — docs/ untouched")
        return 0

    DOCS.mkdir(exist_ok=True)
    for item in DOCS.iterdir():
        if item.name in KEEP:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for item in OUT.iterdir():
        dst = DOCS / item.name
        shutil.copytree(item, dst) if item.is_dir() else shutil.copy2(item, dst)
    (DOCS / ".nojekyll").write_text("")
    if not (DOCS / "index.html").is_file():
        return fail("docs/index.html missing after the copy", 1)
    print(f"docs/ updated ({sum(1 for _ in DOCS.rglob('*') if _.is_file())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
