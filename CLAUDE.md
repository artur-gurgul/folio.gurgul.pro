# folio — project guide for Claude Code

<https://folio.gurgul.pro> — one subject, one A4 page, as dense as it gets.
This file is everything a session needs; it is self-contained on purpose.

## What a folio is — READ FIRST

A folio is a page that helps the reader **remember** a subject: one A4 sheet,
as dense as possible with **important facts**, and **visualisations** wherever
a picture carries a fact better than words. **No noise** — no filler, no
narrative, no padding; every line earns its place by being a fact worth
memorising.

**It is not** interview preparation (no Q&A lists, no "how to answer"), not a
tutorial, not a blog post. A section called "Likely questions" or "Interview
…" does not belong in a folio.

**There is no fixed structure.** Each folio is shaped separately, by its
subject, against the goals: **one A4 page · one subject · dense information,
not wordy explanations · graphs and drawings wherever possible.** The template
is a starting point, not a form to fill in; drop, merge or invent sections as
the subject needs. Repetition is noise: say a fact once.

## Layout

```
src/                     the sources — the only place content is written
  index.md               the front page (what folio is) + the list of folios
  <subject>/<name>.tex   one folio per file, grouped by subject
  .sajt/                 site config + theme (layouts, styles, fonts, sheet style)
tools/build.py           builds src/ → docs/ (needs a compiled Sajt: --sajt or $SAJT)
tools/check.py           the checks (headers, leaks, docs untouched, one page) — no Sajt needed
tools/ci-fonts.py        installs the exact fonts the page-count check needs
tools/templates/folio.tex  the anatomy of a folio — start every new one from it
docs/                    ⚠ BUILD OUTPUT, served by GitHub Pages. Never edit by hand.
.github/                 issue forms, PR template, CODEOWNERS, the checks workflow
CONTRIBUTING.md          how people help: report, fix, suggest, discuss
```

**`main` is protected:** every change — the maintainer's too — goes through a
pull request that passes the checks and is approved by the maintainer. Run
`python3 tools/check.py --compile` before opening one.

`docs/CNAME` is the custom domain — the build keeps it; never delete it.

## Hard rules — content

1. **One A4 page.** The build fails if a folio's PDF runs to a second page.
   Condense; never shrink fonts below the sheet style to cheat.
2. **Dense, but true.** Every fact must be checkable. The header comment lists
   the sources; a section not checked against them carries `\unverified` and
   is never presented as settled. Do not invent facts to fill space — empty
   space is a research task, not a writing task.
3. **Visual where it helps.** A diagram, table or timeline beats a paragraph
   whenever the subject has structure (flows, layers, comparisons, sequences).
4. **Linked.** Tags (`% @tags:`) and the "Related" line connect a folio to its
   neighbours; prefer tags that other folios use too.
5. **A folio owns its page.** Content may start from older notes, but once it
   is here it is folio's: edit it here, adapt it freely to these rules.
6. **No branding.** No personal names, logos, initials or "my notepad" voice —
   on pages, in titles, in metadata. The pages are **folios** (never "memos"
   or "sheets" in anything a reader sees); the site is just *folio*.
7. **Public domain.** Everything here is CC0 1.0 (`LICENSE`); contributions
   are dedicated the same way. Add a third-party file only if its licence
   allows it, and record it in `LICENSES/README.md` with its licence text.

## Hard rules — working

1. **When you are not sure, do not guess — ask.** What a word means here,
   which of two designs is current, what the owner wants. "I could not check
   X" is a valid answer; an invented X is not.
2. **Anything not asked for needs approval before it goes in** — a new page
   element, convention, layout change, or rework of something that works.
   Propose it first. When it overlaps something that exists, ask explicitly:
   **coexist or replace?**
3. **Never rewrite git history.** No `commit --amend`, no `rebase`, no `reset`
   over committed work, no `push --force`. Undo with a new commit
   (`git revert`). This is a public repository: others may have pulled.
4. **Every script that is run is saved, committed in `tools/`, and kept** —
   never deleted, never self-deleting. Scripts are Python, standard library
   only, so a contributor needs nothing extra. If a step needs ad-hoc shell,
   the tooling has a gap: add a script.

## Hard rules — quality

1. **Look at the result before calling it done.** Build, open the rendered
   page and its PDF, and confirm it fits one A4 and reads well. "It compiles"
   is not evidence about anything visual.
2. **Checks never lie.** A check exits **0** pass · **1** failed · **2**
   could not check — "it is broken" and "I learned nothing" are different
   answers. Every check proves it can go red (a positive control) before its
   green means anything.
3. **Nothing internal or secret, anywhere.** This repository and its history
   are public: no hostnames of private machines, private IP addresses, keys,
   tokens, personal data or paths from other projects — not in pages, not in
   comments, not in commit messages.

## Building

```sh
python3 tools/build.py --sajt /path/to/compiled/sajt     # or: SAJT=… python3 tools/build.py
python3 tools/build.py --sajt … --check                  # build only, docs/ untouched
```

Needs Node.js, and for folios TeX Live (xelatex) + poppler (pdftocairo,
pdfinfo). Sajt is not public yet: **contributors change `src/` only**; the
maintainer builds and commits `docs/`. Without Sajt, say so — do not
hand-write anything under `docs/`.

## Writing a folio

Use the `new-folio` skill (`.claude/skills/new-folio/`): it walks through the
anatomy, the density checklist, the build and the look.
