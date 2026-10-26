# CommonMark audit

Target: CommonMark 0.31.2, all 652 official examples.

## Results

| Configuration | Passed | Failed |
| --- | ---: | ---: |
| Previous application: Python-Markdown 3.7 with fenced_code, sane_lists, tables | 370 | 282 |
| Debian markdown-it-py 3.0.0, CommonMark preset | 649 | 3 |
| Replacement: markdown-it-py 4.0.0, CommonMark preset | 652 | 0 |

The Debian 3.0.0 differences are examples 354 (emphasis with currency symbols),
625 and 626 (HTML comments). No official examples are skipped or marked as
expected failures. The parser tests compare HTML using the upstream CommonMark
normalizer, which ignores insignificant serialization differences. Raw exact
string matching is not the pass criterion.

The baseline and replacement JSON reports include fixture hashes, parser
versions and all mismatches. The fixtures and their licence notices are in
`tests/commonmark/` and work offline.

## Preview checks

The GTK preview is exercised without exceptions on all 652 official inputs.
This is a smoke test, not a screenshot or semantic equivalence test.

Additional regression checks verify ordered-list starting numbers, preserved
inline-code spacing, nonbreaking spaces, code tabs, nested fenced code and
the table-extension toggle. Existing save/open/unsaved-change tests and table
alignment and displayed-width tests also pass against the replacement.

## What can be claimed

**The replacement parsing layer passes all official CommonMark 0.31.2 examples
in core mode.** This is a measured result, not certification and not a claim
that every possible Markdown document has been tested.

**The entire native GTK preview is not yet fully CommonMark-conformant.**
Known gaps include:

- Images now render locally and, after an explicit load action, from HTTP/S.
  Focused GTK tests cover paths, references, scaling, fallbacks, linked images,
  tables and remote-load lifecycle. Animation is a static frame; this has not
  undergone exhaustive browser-equivalent visual comparison.
- Links now use clickable labels, optional hover titles, note-relative file
  resolution and keyboard activation. These have focused GTK tests; link
  interaction is not certified by the official HTML parser suite.
- Raw HTML is reduced to supported native text styling; browser layouts are
  not reproduced, and scripts/styles are ignored.
- Complex list/blockquote spacing and indentation are approximations and
  have not undergone exhaustive visual or semantic comparison.
- Code-block language metadata is not exposed in the UI.

Tables are an optional extension, not part of CommonMark. They remain enabled
initially to preserve existing notes. Turn off **Enable GitHub Flavored Markdown (GFM)** in
the menu for core CommonMark interpretation. The strict suite tests the same
shared parsing function with that extension disabled; table rendering has
separate regression tests.

Do not describe My Notes as fully CommonMark-compliant until these preview
gaps have been resolved and independently verified.

## Rerun

```sh
.venv/bin/python tests/check_commonmark.py --report docs/commonmark-results.json
PYTHONPATH=. .venv/bin/python tests/check_commonmark_preview.py
PYTHONPATH=. .venv/bin/python tests/check_editor.py
PYTHONPATH=. .venv/bin/python tests/check_preview.py
PYTHONPATH=. .venv/bin/python tests/check_table_layout.py
```

Run GTK checks within a graphical session. For SSH into this development VM,
set `WAYLAND_DISPLAY=wayland-0`. To reproduce the former parser results while
Debian's python3-markdown is installed, run
`python3 tests/check_commonmark.py --legacy`.

Sources: https://spec.commonmark.org/0.31.2/ and
https://github.com/commonmark/commonmark-spec/tree/0.31.2/test.
