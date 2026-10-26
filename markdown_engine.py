"""CommonMark parsing, independently testable without GTK.

Tables are an explicit extension; leave them disabled for strict core syntax.
The resulting HTML is consumed by the native preview, never executed.
"""
from markdown_it import MarkdownIt, __version__ as PARSER_VERSION
from urllib.parse import urlsplit

_commonmark = MarkdownIt("commonmark")
_with_tables = MarkdownIt("commonmark").enable("table")

# Native previews intentionally support local file links and images. Keep
# markdown-it's other URL restrictions (javascript, data, vbscript) intact.
for _parser in (_commonmark, _with_tables):
    _default_validation = _parser.validateLink
    _parser.validateLink = lambda url, validate=_default_validation: (
        urlsplit(url).scheme.lower() == "file" or validate(url))


def render_markdown(source, *, tables=False):
    parser = _with_tables if tables else _commonmark
    return parser.render(source)
