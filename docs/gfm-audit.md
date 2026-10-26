# GFM support and verification

GFM mode uses cmarkgfm 2025.10.22, Python bindings to GitHub's reference parser.
Core CommonMark mode continues to use markdown-it-py 4.0.0 and passes all
652 official CommonMark 0.31.2 examples.

The single **Enable GitHub Flavored Markdown (GFM)** switch controls:

- Tables, retaining the app's alignment, sizing and alternating row colours.
- Task-list checkboxes, including nested and completed tasks.
- Strikethrough with one or two tildes, including formatted table cells.
- Extended autolinks for bare web and email addresses (and XMPP addresses).
- The GFM raw HTML tag filter.

Checkboxes are semantic native GTK controls displayed read-only. Change the
source marker `[ ]`, `[x]` or `[X]` to edit completion. They replace list
bullets, and wrapped task text has a hanging indent.

Code spans and fenced code do not acquire task, strike or bare-link formatting.
Disabling GFM removes all of these extensions together without changing the
source text or modified state. Explicit CommonMark links continue to work.

## Official extension examples

Published specification: https://github.github.com/gfm/ (0.29-gfm).
All 28 examples in its five extension sections are compared, with no skips.

| Section | Passed | Total |
| --- | ---: | ---: |
| Tables | 8 | 8 |
| Task list items | 2 | 2 |
| Strikethrough | 3 | 3 |
| Extended autolinks | 12 | 14 |
| Disallowed raw HTML | 1 | 1 |
| **Total** | **26** | **28** |

Known differences: examples 634 and 635 concern how XMPP resource paths
containing `@` or an additional `/` are autolinked by the reference library.
`docs/gfm-results.json` records exact source, expected HTML and actual HTML.
The test exits with a failure while these differences remain. They are not
silently ignored or converted into passes. Do not claim full GFM conformance.

The additional full-page comparison is retained in
`docs/gfm-full-results.json`: **653/677** outputs match. Its other 22
differences are outside the extension sections, in the older underlying core
examples and HTML/filtering expectations. This is a separate target from
CommonMark 0.31.2, which remains 652/652 in core mode. The full comparison is
also not a passing conformance result.

These examples target parsing. GTK-specific tests separately verify displayed
checkbox states, task indentation, strike styling, table links and all-feature
mode switching. Existing list, image, link, table and editor tests also run.
The native preview's previously documented raw HTML and layout limits remain.

Footnotes, maths, Mermaid diagrams, alerts and GitHub-specific issue/mention
links are not part of these five GFM extensions and are not enabled here.

## Repeat checks

```sh
.venv/bin/python tests/check_commonmark.py
.venv/bin/python tests/check_gfm_spec.py --report docs/gfm-results.json
PYTHONPATH=. .venv/bin/python tests/check_gfm.py
```

The official GFM check currently reports the two known XMPP differences above.
Fixtures and attribution are retained in `tests/gfm/`; they work offline.
