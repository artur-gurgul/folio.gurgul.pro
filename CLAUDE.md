# folio — project guide for Claude Code

<https://folio.gurgul.pro> — one subject, one A4 page, as dense as it gets.
This file is everything a session needs; it is self-contained on purpose.

## What a folio is — READ FIRST

A folio is a page that helps the reader **remember** a subject: one A4 sheet,
as dense as possible with **important facts**, and **visualisations** wherever
a picture carries a fact better than words. **No noise** — no filler, no
narrative, no padding; every line earns its place by being a fact worth
memorising.

**It is for learning, not for looking things up.** A folio is for people who
want to understand ideas, remember them and see them — and to have fun doing
it. Prefer the mechanism behind a feature, the idea that makes it click, the
surprising number, the history that explains a quirk, the trick nobody writes
down. **When something is interesting and hard to find on the internet, it
belongs on the folio** — that is worth more than what is on the first page of
the manual.

**It is not documentation.** A folio that reads like a manual — option lists for
their own sake, "X is used to Y", an API surface copied from the reference — has
failed, however correct it is. **Documentation voice is a red flag**, not a style
choice: rewrite it as the idea, the mechanism or a picture, or cut it. The manual
already exists; link to it (see "Links and references" below).

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
  index.md               the front page — only what folio is
  folios.md              the list of folios (filtered by the sidebar's search and areas)
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

**How a page is built.** A page's HTML is its own content and nothing else, in
plain `<main>` (`layouts/default.pug`, `layouts/memos.pug`): it reads well with
JavaScript off, and it is what a crawler reads. Then the CSS and the scripts
load. `static/js/site.js` adds the side panel in front of `<main>` and fills it
from `nav.json`; on the list page `static/js/memos.js` adds tags and the filter
from `memos/index.json` (and `memos/search.json` when someone searches).
Content first, menus after. With JavaScript on, the CSS keeps the panel's place
from the first paint (`@media (scripting: enabled)` in `all.css`), so the
content does not move when the panel arrives. With JavaScript off there is no
menu at all: the front page alone carries a **site map** (`sitemap: true` in
`src/index.md`) — the subject groups, each linking to its part of the list —
hidden whenever JavaScript is on. Groups, not folios, so it stays small as the
site grows. The build writes `nav.json`,
`sitemap.xml` and `robots.txt` (`generate:` in `src/.sajt/config.yaml`) and
fails without them. Do not put anything into a page that every page repeats —
it belongs in a JSON file, a stylesheet or a script.

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
   **One discussion thread per folio:** its number is the hidden label
   `discussion=<n>` in `% @labels:` (GitHub Discussions, category *Folio
   comments*). "Discuss this folio" opens that thread; a folio without one
   starts it — then record the new thread's number in the folio.
5. **A folio owns its page.** Content may start from older notes, but once it
   is here it is folio's: edit it here, adapt it freely to these rules.
6. **No branding.** No personal names, logos, initials or "my notepad" voice —
   on pages, in titles, in metadata. The pages are **folios** (never "memos"
   or "sheets" in anything a reader sees); the site is just *folio*.
7. **Public domain.** Everything here is CC0 1.0 (`LICENSE`); contributions
   are dedicated the same way. Add a third-party file only if its licence
   allows it, and record it in `LICENSES/README.md` with its licence text.
8. **Links and references live on the web; paper has none.** A printed folio
   cannot hold a link and has no room for references — the website can. So the
   source marks both, and the PDF shows neither:
   - **Linked text:** `\link{text}{url}` — on paper the text alone, on the web
     a link. Define it in the folio's preamble (the template has it), because
     the website's renderer reads macros from the folio itself:
     `\newcommand\link[2]{\pdfonly{#1}\htmlonly{\href{#2}{#1}}}`.
     Never put a bare URL in the printed text.
   - **Further reading:** a block that only the website shows, last in the
     body, before the Related line — a few links worth a reader's time (the
     manual, the spec, a talk, a blog post or paper that is hard to find), each
     with one line on why:
     ```latex
     \begin{htmlonly}
     \section{Further reading}
     \begin{itemize}
       \item \href{https://…}{Title} — why it is worth reading
     \end{itemize}
     \end{htmlonly}
     ```
     On paper it prints nothing and takes no space.
   - **The `% Sources` header stays.** It is the fact-check trail for whoever
     edits the folio; Further reading is for readers. A link in either must be
     `https://` and point where it says.

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
pdfinfo), and a Sajt that supports `generate:` (it writes `nav.json`,
`sitemap.xml` and `robots.txt`; the build fails without them). Sajt is not public yet: **contributors change `src/` only**; the
maintainer builds and commits `docs/`. Without Sajt, say so — do not
hand-write anything under `docs/`.

## Writing a folio

Use the `new-folio` skill (`.claude/skills/new-folio/`): it walks through the
anatomy, the density checklist, the build and the look.
