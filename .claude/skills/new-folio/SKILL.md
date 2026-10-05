---
name: new-folio
description: Writing, adapting or densifying a folio page (src/<subject>/<name>.tex) — anatomy, density checklist, build, one-page check, and looking at the result.
---

# Writing a folio

A folio = one subject, one A4 page, dense facts + pictures, no noise, not
interview prep. The rules are in `CLAUDE.md`; this is the procedure.

## 1. Decide before writing

- **Subject and file:** `src/<subject>/<name>.tex` — kebab-case, the subject
  folder is the area shown on the site. Reuse an existing subject folder.
- **Sources:** list where every fact can be checked. No source → ask, or mark
  the section `\unverified`. Never fill space with invented facts.
- **Overlap:** search `src/` for folios on the same ground. Overlapping an
  existing one is a question for the owner — *coexist or replace?* — not a
  silent duplicate.

## 2. Write from the template

Start from `tools/templates/folio.tex`. Keep its header comment (description,
`Sources:`, `@labels:`, `@tags:`). Parts, in order:

| Part | Purpose |
|---|---|
| `\sheettitle{Title}{subject · folio}` | the subject, named the way readers search for it |
| `\oneliner{…}` | the one sentence worth keeping if nothing else is |
| a `tikzpicture` / table | structure first: flows, layers, comparisons, timelines |
| `How it works` | the mechanism, as dense bullet facts |
| `Example` | the smallest code or case that shows it |
| `Traps` | misconceptions stated as facts (never "interview" anything) |
| `Remember` | the bold takeaway |
| `Related:` line | neighbouring folios / subjects |

Adapting older notes: drop Q&A lists and "Likely questions", rename
"Interview traps" → "Traps", drop labels like `level=` or study rounds.

## 3. Density checklist — every line must pass

- Is it a **fact** (checkable), not narrative or encouragement?
- Would a reader **lose something** if it went? If not, cut it.
- Could a **picture or table** say it in less space? Then draw it.
- Is the page **full**? Empty space on the A4 is room for more facts — find
  them in the sources; do not pad.

## 4. Build, check, look

```sh
python3 tools/build.py --sajt "$SAJT"     # fails if any folio PDF is not ONE page
```

Then **open the result** — `docs/<subject>/<name>.html` (web page) and
`docs/<subject>/<name>.pdf` (the printed sheet) — and check: one page, nothing
clipped, figures readable, the table fits. No Sajt available? Say so; do not
edit `docs/` by hand.

## 5. Before committing

- Nothing internal: no private hostnames, IPs, keys, personal data, or paths
  from other projects — in the page, its comments, or the commit message.
- One folio (or one coherent change) per commit; never amend, never force-push.
