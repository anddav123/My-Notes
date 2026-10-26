"""CommonMark parsing, independently testable without GTK.

GFM is an explicit mode; leave it disabled for strict core syntax.
The resulting HTML is consumed by the native preview, never executed.
"""
from markdown_it import MarkdownIt, __version__ as PARSER_VERSION
from urllib.parse import urlsplit
from importlib.metadata import version
from cmarkgfm.cmark import Options, markdown_to_html_with_extensions

GFM_PARSER_VERSION = version("cmarkgfm")

_commonmark = MarkdownIt("commonmark")

# Native previews intentionally support local file links and images. Keep
# markdown-it's other URL restrictions (javascript, data, vbscript) intact.
for _parser in (_commonmark,):
    _default_validation = _parser.validateLink
    _parser.validateLink = lambda url, validate=_default_validation: (
        urlsplit(url).scheme.lower() == "file" or validate(url))


def render_markdown(source, *, gfm=False, tables=None):
    # Retain the old keyword for scripts written before the mode was expanded.
    if tables is not None:
        gfm = tables
    if gfm:
        # Native GTK consumes this output; it is never executed in a browser.
        # Keep raw HTML for native rendering and local-file URLs. GFM's
        # tagfilter still applies; URI/image handlers validate before opening.
        return markdown_to_html_with_extensions(
            source, options=Options.CMARK_OPT_UNSAFE,
            extensions=["table", "autolink", "tagfilter", "strikethrough", "tasklist"])
    return _commonmark.render(source)
