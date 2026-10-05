#!/usr/bin/env python3
"""ci-fonts.py — install the exact fonts the folio sheet style uses (for the page-count check).

A folio must fit one A4 page, and where lines break depends on the fonts. So a
machine that checks page counts must have the SAME font files the site is built
with: Atkinson Hyperlegible (body) and 0xProto Nerd Font Mono (code). Each file
below is downloaded from a fixed URL and verified against its sha256 before it
is installed into ~/.local/share/fonts/folio — a mismatch stops with exit 2.

Both families are SIL OFL 1.1; they are fetched at check time, not committed.

USAGE
  python3 tools/ci-fonts.py                 # download, verify, install, fc-cache
  python3 tools/ci-fonts.py --dest DIR      # install somewhere else

EXIT: 0 installed and visible to fontconfig · 2 could not install
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

GF = "https://raw.githubusercontent.com/google/fonts/8772f86137e17678cbd3584ca9a3c9486c3e7e50/ofl/atkinsonhyperlegible"
MANIFEST = [
    # sha256, url, files to install (None = the file itself)
    ("7fb917c89019896d0b52ee84b7cbb3304c18cb90b19a62f5e32712bd23e97669", f"{GF}/AtkinsonHyperlegible-Regular.ttf", None),
    ("5a3b0c8cc8ca545155150b4512a1fa248298df121c50d6557e651e61fbdab92f", f"{GF}/AtkinsonHyperlegible-Bold.ttf", None),
    ("021beda4d3c6edfc78872e436d74009f9a1bcb294331908fe5747c61d3dcc514", f"{GF}/AtkinsonHyperlegible-Italic.ttf", None),
    ("7a46f1b0ef2f64b61065c1a6b5a11fcb9b019b44062d88ba121a083cc39e86bf", f"{GF}/AtkinsonHyperlegible-BoldItalic.ttf", None),
    ("effaa4c257c1f25e6d2d50679e9b845eab36b346dea9ee26f4405da1a21e6428",
     "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/0xProto.tar.xz",
     "0xProtoNerdFontMono-"),
]
FAMILIES = ("Atkinson Hyperlegible", "0xProto Nerd Font Mono")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=str(Path.home() / ".local/share/fonts/folio"))
    args = ap.parse_args()
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    for sha, url, member_prefix in MANIFEST:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "folio-ci"}),
                                    timeout=120) as resp:
            data = resp.read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            print(f"COULD-NOT-RUN: {url}\n  sha256 {got}\n  expected {sha} — refusing to install", file=sys.stderr)
            return 2
        if member_prefix is None:
            (dest / url.rsplit("/", 1)[-1]).write_bytes(data)
            print(f"installed {url.rsplit('/', 1)[-1]}")
            continue
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
            members = [m for m in tf.getmembers()
                       if Path(m.name).name.startswith(member_prefix) and m.name.endswith(".ttf")]
            if not members:
                print(f"COULD-NOT-RUN: no {member_prefix}*.ttf inside {url}", file=sys.stderr)
                return 2
            for m in members:
                (dest / Path(m.name).name).write_bytes(tf.extractfile(m).read())
                print(f"installed {Path(m.name).name}")

    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(dest)], check=False)
        listed = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
        missing = [f for f in FAMILIES if f not in listed]
        if missing:
            print(f"COULD-NOT-RUN: fontconfig does not see {missing}", file=sys.stderr)
            return 2
        print(f"fontconfig sees: {', '.join(FAMILIES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
