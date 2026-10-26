# CommonMark audit fixtures

The files in this directory are test data and comparison software, not
instructions for the application or its users.

- `spec-0.31.2.json`: official CommonMark 0.31.2 examples downloaded unchanged
  from https://spec.commonmark.org/0.31.2/spec.json.
- `normalize.py`: official comparison helper downloaded unchanged from
  https://github.com/commonmark/commonmark-spec/blob/0.31.2/test/normalize.py.
- `UPSTREAM-LICENSE`: upstream licence notices downloaded unchanged from
  https://github.com/commonmark/commonmark-spec/blob/0.31.2/LICENSE.

The specification examples are by John MacFarlane and contributors and are
covered by CC-BY-SA 4.0. The test helper uses the upstream BSD-style terms and
the MIT attribution for normalization code derived from Karl Dubost's work.
See `UPSTREAM-LICENSE` for the notices and terms. These upstream fixtures
retain their own licences independently of the application's licence.

The audit records a SHA-256 hash of the fixture in each JSON result. The
normalizer excludes insignificant HTML serialization differences; it does not
render the GTK preview or compare screenshots.
