# Contributing to folio

A folio is one subject on one A4 page: dense facts and pictures, no noise —
written to learn and remember ideas, not to look things up. **It is not
documentation**: a folio that reads like a manual has missed the point; the
interesting, hard-to-find fact is what it is for. Help is welcome — reviewing
facts is as valuable as writing them.

## Ways to help

| You want to… | Do this |
|---|---|
| **Report a wrong or outdated fact** | "Report a problem" under the folio, or open a [fact correction](https://github.com/artur-gurgul/folio.gurgul.pro/issues/new?template=fact-correction.yml). Include a source — a correction without one cannot be accepted. |
| **Fix it yourself** | "LaTeX source" at the top of the folio opens its source on GitHub; the ✎ pencil there edits it, and GitHub creates the pull request for you. |
| **Suggest a new folio** | [Suggest a folio](https://github.com/artur-gurgul/folio.gurgul.pro/issues/new?template=folio-suggestion.yml): the subject, the facts worth keeping, a picture, sources. |
| **Report a broken page** | [Website problem](https://github.com/artur-gurgul/folio.gurgul.pro/issues/new?template=website-problem.yml). |
| **Talk about a folio** | "Discuss this folio" under the folio starts a thread in the *Folio comments* category of [Discussions](https://github.com/artur-gurgul/folio.gurgul.pro/discussions). Discussions live on GitHub under GitHub's terms — they are not part of this repository's CC0 content. |
| **Discuss an idea** | [Discussions](https://github.com/artur-gurgul/folio.gurgul.pro/discussions). |

## Pull requests

- Change files under **`src/`** only. `docs/` is the built site; the maintainer
  rebuilds it after merging — a pull request that edits `docs/` fails its check.
- Keep to the rules in [`CLAUDE.md`](CLAUDE.md): one A4 page, one subject,
  facts with sources, pictures where possible, no documentation voice, no
  interview Q&A, nothing internal or personal.
- Links are for the website only: mark linked text with `\link{text}{url}` and
  put reading suggestions in a `Further reading` block inside
  `\begin{htmlonly}` — paper shows neither (see [`CLAUDE.md`](CLAUDE.md), rule 8).
- Run the checks before you open it (Python 3, standard library):

  ```sh
  python3 tools/check.py              # headers + leaks
  python3 tools/check.py --compile    # + one page per folio (needs TeX Live xetex, poppler,
                                      #   and the fonts: python3 tools/ci-fonts.py)
  ```

  GitHub runs the same checks on every pull request.
- Every change is reviewed by the maintainer before it is merged.

## Licence

By contributing you dedicate your contribution to the public domain under
[CC0 1.0](LICENSE), like the rest of folio.
