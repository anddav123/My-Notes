# GFM specification fixtures

Source: https://github.github.com/gfm/, published as GFM 0.29-gfm.
Attribution: GitHub, John MacFarlane and contributors. The specification is
licensed under CC-BY-SA 4.0, as linked in the published specification.
https://creativecommons.org/licenses/by-sa/4.0/

`spec-0.29-gfm.json` is derived from the 677 examples on that official page.
`tools/extract_gfm_examples.py` extracts the code blocks, decodes HTML entities,
and converts the specification's visual tab arrows back to tab characters.
No example's expected HTML is changed to match the application.

The default test checks all 28 examples in the five extension sections:
tables, task lists, strikethrough, extended autolinks, and disallowed raw HTML.
`--all` also compares the older specification's underlying CommonMark cases;
those are distinct from the application's CommonMark 0.31.2 target.

Tests reuse the CommonMark HTML normalization helper and retain its upstream
licences in `tests/commonmark/`. The fixtures retain their upstream licence
independently of the application's licence.
