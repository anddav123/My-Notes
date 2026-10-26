"""CommonMark parsing, independently testable without GTK.

Tables are an explicit extension; leave them disabled for strict core syntax.
The resulting HTML is consumed by the native preview, never executed.
"""
from markdown_it import MarkdownIt, __version__ as PARSER_VERSION

_commonmark = MarkdownIt("commonmark")
_with_tables = MarkdownIt("commonmark").enable("table")


def render_markdown(source, *, tables=False):
    parser = _with_tables if tables else _commonmark
    return parser.render(source)
