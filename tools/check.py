#!/usr/bin/env python3
"""check.py — folio's checks: run them before a pull request; GitHub runs them on every one.

Standard library only, and no Sajt needed — anyone can run it.

CHECKS
  headers   every folio (src/**/*.tex) has a "% Sources" line and a "% @labels:" line
  leaks     no private IP addresses, MAC addresses, private keys or key-like
            assignments in any tracked text file — this repository is public
  docs      with --base REF: the change does not touch docs/ (build output; the
            maintainer rebuilds it). --allow-docs skips it (maintainer changes)
  compile   with --compile: every folio compiles with xelatex and is exactly
            ONE A4 page. Needs TeX Live (xetex) + poppler + the fonts the sheet
            style uses (tools/ci-fonts.py installs the exact ones)
  figures   every published figure (docs/**/*-figN.svg) is recoloured for the
            dark page, and its text is at least 4.5:1 on it (tools/dark-figures.py)

  --selftest  every check must flag a planted bad sample first (a positive
              control); a check that cannot go red proves nothing

USAGE
  python3 tools/check.py                         # headers + leaks
  python3 tools/check.py --compile               # + one page per folio
  python3 tools/check.py --base origin/main      # + docs/ untouched
  python3 tools/check.py --selftest --compile    # prove each check can fail, then run

EXIT: 0 pass · 1 a check failed · 2 could not check
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
STY_DIR = SRC / ".sajt" / "tex"
TEXT = {".tex", ".md", ".yml", ".yaml", ".pug", ".html", ".css", ".js", ".json",
        ".svg", ".py", ".txt", ".sty", ""}
LEAKS = {
    "private IPv4": re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    "MAC address": re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "key assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{16,}"),
}

results: list[tuple[str, str, str]] = []   # (verdict, name, detail)


def say(verdict: str, name: str, detail: str = "") -> None:
    results.append((verdict, name, detail))
    print(f"  {verdict:<4} {name}")
    for line in detail.splitlines():
        print(f"         {line}")


def folios() -> list[Path]:
    """The folio sources: src/**/*.tex outside hidden dirs — src/.build holds the
    build's own copy of each .tex and src/.sajt the theme, neither is a folio."""
    return sorted(p for p in SRC.rglob("*.tex")
                  if not any(part.startswith(".") for part in p.relative_to(SRC).parts))


def header_problems(text: str) -> list[str]:
    head = text.split("\\documentclass", 1)[0]
    missing = []
    if not re.search(r"^% Sources\b", head, re.M):
        missing.append('no "% Sources" line in the header')
    if not re.search(r"^% @labels:", head, re.M):
        missing.append('no "% @labels:" line in the header')
    return missing


def leak_hits(text: str) -> list[str]:
    return [f"L{n} [{name}] {m.group(0)}"
            for n, line in enumerate(text.splitlines(), 1)
            for name, rx in LEAKS.items() for m in rx.finditer(line)]


def pdf_pages(tex: Path, workdir: Path) -> tuple[int | None, str]:
    """Compile one folio; (pages, log tail). None = it did not compile."""
    env = dict(os.environ, TEXINPUTS=f"{STY_DIR}//:")
    run = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                          f"-output-directory={workdir}", str(tex)],
                         cwd=tex.parent, env=env, capture_output=True, text=True,
                         errors="replace", timeout=300)
    pdf = workdir / (tex.stem + ".pdf")
    if run.returncode != 0 or not pdf.is_file():
        return None, run.stdout[-1500:]
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
    pages = next((ln.split()[-1] for ln in info.stdout.splitlines() if ln.startswith("Pages:")), "")
    return (int(pages) if pages.isdigit() else None), ""


def tracked() -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True)
    return [ROOT / p for p in out.stdout.splitlines() if p]


def check_headers() -> None:
    found = folios()
    if not found:
        say("CNC", "headers", "no folios found under src/")
        return
    bad = [f"{f.relative_to(ROOT)}: {', '.join(p)}"
           for f in found if (p := header_problems(f.read_text(errors="replace")))]
    say("FAIL" if bad else "PASS", f"headers — {len(found)} folio(s) carry Sources + labels",
        "\n".join(bad))


def check_leaks() -> None:
    files = [p for p in tracked() if p.is_file() and p.suffix.lower() in TEXT]
    bad = [f"{p.relative_to(ROOT)}: {h}" for p in files
           for h in leak_hits(p.read_text(errors="replace"))]
    say("FAIL" if bad else "PASS", f"leaks — {len(files)} text file(s) scanned",
        "\n".join(bad[:40]))


def check_docs(base: str) -> None:
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", f"{base}...HEAD", "--", "docs/"],
                          capture_output=True, text=True)
    if diff.returncode != 0:
        say("CNC", "docs", f"git diff against {base} failed: {diff.stderr.strip()}")
        return
    touched = [p for p in diff.stdout.splitlines() if p]
    say("FAIL" if touched else "PASS", "docs — build output not edited by hand",
        ("these are generated; change src/ instead:\n" + "\n".join(touched)) if touched else "")


def check_compile() -> None:
    missing = [t for t in ("xelatex", "pdfinfo") if not shutil.which(t)]
    if missing:
        say("CNC", "compile", f"not installed: {', '.join(missing)} (TeX Live xetex, poppler-utils)")
        return
    found = folios()
    bad, ok = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for f in found:
            pages, log = pdf_pages(f, Path(tmp))
            if pages is None:
                bad.append(f"{f.relative_to(ROOT)}: does not compile\n{log}")
            elif pages != 1:
                bad.append(f"{f.relative_to(ROOT)}: {pages} pages — a folio must fit ONE page")
            else:
                ok += 1
    say("FAIL" if bad else "PASS", f"compile — {ok}/{len(found)} folio(s) are one A4 page",
        "\n".join(bad))


def dark_figures(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "tools" / "dark-figures.py"), *args],
                          capture_output=True, text=True)


def check_figures() -> None:
    run = dark_figures(str(ROOT / "docs"), "--check")
    summary = (run.stdout.strip().splitlines() or [""])[-1]
    if run.returncode == 2:
        say("CNC", "figures", (run.stdout + run.stderr).strip())
        return
    say("FAIL" if run.returncode else "PASS", f"figures — {summary}",
        "\n".join(run.stdout.strip().splitlines()[:-1][:20]))


def selftest(with_compile: bool) -> bool:
    """Positive controls: each check's core must flag a planted bad sample."""
    controls = [
        ("headers flags a folio without Sources/labels",
         bool(header_problems("% just a comment\n\\documentclass{article}"))),
        # the planted samples are assembled at run time: written out literally
        # they would sit in this tracked file and the leak scan would flag itself
        ("leaks flags a private IP and a key",
         len(leak_hits("host " + ".".join(["192", "168", "1", "20"]) + "\n"
                       + "api" + "_key = '" + "x" * 24 + "'")) >= 2),
        # its own controls: a paper figure and a too-faint text colour must both fail
        ("figures flags a paper figure and faint text", dark_figures("--selftest").returncode == 0),
    ]
    if with_compile and shutil.which("xelatex") and shutil.which("pdfinfo"):
        template = ROOT / "tools" / "templates" / "folio.tex"
        if template.is_file():
            with tempfile.TemporaryDirectory() as tmp:
                two = Path(tmp) / "two-pages.tex"
                two.write_text(template.read_text().replace(
                    "\\end{document}", "\\clearpage second page\n\\end{document}"))
                pages, _ = pdf_pages(two, Path(tmp))
                controls.append(("compile counts a two-page folio as 2 pages", pages == 2))
    all_red = True
    for name, went_red in controls:
        print(f"  {'PASS' if went_red else 'FAIL'} positive control: {name}")
        all_red &= went_red
    return all_red


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="", help="git ref the change is based on (enables the docs check)")
    ap.add_argument("--allow-docs", action="store_true", help="skip the docs check (maintainer changes)")
    ap.add_argument("--compile", action="store_true", help="compile every folio, assert one page")
    ap.add_argument("--selftest", action="store_true", help="prove each check can fail first")
    args = ap.parse_args()

    print("folio checks")
    if args.selftest and not selftest(args.compile):
        print("RESULT: COULD-NOT-CHECK — a positive control did not go red")
        return 2
    check_headers()
    check_leaks()
    check_figures()
    if args.base and not args.allow_docs:
        check_docs(args.base)
    if args.compile:
        check_compile()

    verdicts = [v for v, _, _ in results]
    if "FAIL" in verdicts:
        print(f"RESULT: FAIL — {verdicts.count('FAIL')} check(s) failed")
        return 1
    if "CNC" in verdicts:
        print("RESULT: COULD-NOT-CHECK — see above")
        return 2
    print(f"RESULT: PASS — {len(verdicts)} check(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
