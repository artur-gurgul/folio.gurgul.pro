# folio

**One subject, one A4 page, as dense as it gets** — <https://folio.gurgul.pro>

Each folio is a page for *remembering* a subject: the important facts, and the
pictures that carry them, packed onto a single printable A4 sheet. No filler,
no narrative, nothing to skip. Every folio is a web page and a one-page PDF.

It is not interview preparation, not a tutorial and not a blog post. It is the
page you keep next to you.

## How it is made

- `src/<subject>/<name>.tex` — one folio per file (LaTeX + TikZ). Start from
  `tools/templates/folio.tex`.
- `src/index.md` — the front page.
- `tools/build.py` — builds `src/` into `docs/` with Sajt, a small static-site
  generator; `docs/` is what GitHub Pages serves.
  The build fails if a folio does not fit on one page.

## Contributing

Change files under `src/` and open a pull request. Please keep to the rules in
[`CLAUDE.md`](CLAUDE.md) — they apply to people as much as to Claude Code:
dense, true (sources in the header), visual, one page, nothing internal. Do
not edit `docs/`; the maintainer rebuilds it.

## Licence

**Public domain — [CC0 1.0](LICENSE).** Use the folios for anything, no
attribution needed. Contributions are dedicated the same way. The bundled fonts
(SIL OFL 1.1) and the code-highlighting theme (BSD 3-Clause) keep their own
licences — see [`LICENSES/`](LICENSES/README.md).
