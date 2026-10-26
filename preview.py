"""Render Markdown as styled native GTK text without loading web content."""
from html.parser import HTMLParser
from html import escape
import re

import markdown
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango


class MarkdownText(HTMLParser):
    STYLES = {"strong": "bold", "b": "bold", "em": "italic", "i": "italic",
              "code": "code", "pre": "pre", "blockquote": "quote",
              "a": "link", **{f"h{i}": f"h{i}" for i in range(1, 7)}}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs = []
        self.stack = []
        self.lists = []
        self.hidden = 0
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.cell_header = False
        self.cell_align = 0.0
        self.trailing_newlines = 0

    def add(self, text):
        if text:
            styles = tuple(self.STYLES[tag] for tag, _attrs in self.stack if tag in self.STYLES)
            if self.cell is not None:
                self.cell.append((text, styles))
            elif self.table is None:
                self.runs.append((text, styles))
                self.trailing_newlines = (self.trailing_newlines + len(text) if not text.strip("\n")
                                          else len(text) - len(text.rstrip("\n")))

    def newline(self, count=1):
        if self.runs:
            self.add("\n" * max(0, count - self.trailing_newlines))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.hidden += 1
        if self.hidden:
            return
        if tag == "table":
            self.newline(2)
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.cell_header = tag == "th"
            style = attrs.get("style", "")
            self.cell_align = 1.0 if "right" in style else 0.5 if "center" in style else 0.0
        if tag in ("p", "pre", "blockquote") or re.fullmatch("h[1-6]", tag):
            self.newline(2)
        if tag in ("ul", "ol"):
            self.newline()
            self.lists.append([tag, 0])
        if tag == "li":
            self.newline()
            if self.lists:
                self.lists[-1][1] += 1
                kind, number = self.lists[-1]
                self.add("  " * (len(self.lists) - 1) + (f"{number}. " if kind == "ol" else "• "))
        if tag == "br":
            self.add("\n")
        elif tag == "hr":
            self.newline(2)
            self.add("────────────")
            self.newline(2)
        elif tag == "img":
            self.add(f"[Image: {attrs.get('alt') or 'image'}]")
        else:
            self.stack.append((tag, attrs))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ("img", "br", "hr"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ("td", "th") and self.cell is not None:
            self.row.append((self.cell, self.cell_header, self.cell_align))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None
            self.runs.append(("\ufffc", (f"table:{len(self.tables) - 1}",)))
            self.trailing_newlines = 0
            self.newline(2)
        matching = next((i for i in range(len(self.stack) - 1, -1, -1)
                         if self.stack[i][0] == tag), None)
        if tag == "a" and matching is not None:
            href = self.stack[matching][1].get("href", "")
            if href:
                self.add(f" ({href})")
        if matching is not None:
            del self.stack[matching:]
        if tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self.newline(1 if self.lists else 2)
        elif tag == "li":
            self.newline()
        elif tag in ("p", "pre", "blockquote") or re.fullmatch("h[1-6]", tag):
            self.newline(2)

    def handle_data(self, data):
        if self.hidden:
            return
        if not any(tag == "pre" for tag, _attrs in self.stack):
            # Ignore the HTML serializer's whitespace between block elements.
            if data.isspace() and "\n" in data:
                return
            data = re.sub(r"\s+", " ", data)
        self.add(data)


def parse_markdown(source):
    parser = MarkdownText()
    parser.feed(markdown.markdown(source, extensions=["fenced_code", "sane_lists", "tables"]))
    parser.close()
    return parser


class MarkdownPreview(Gtk.TextView):
    def __init__(self):
        super().__init__(editable=False, cursor_visible=False,
                         wrap_mode=Gtk.WrapMode.WORD_CHAR,
                         left_margin=24, right_margin=24, top_margin=24, bottom_margin=24,
                         hexpand=True, vexpand=True)
        self.update_property([Gtk.AccessibleProperty.LABEL], ["Markdown preview"])
        self.table_widgets = []
        buffer = self.get_buffer()
        buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        buffer.create_tag("italic", style=Pango.Style.ITALIC)
        buffer.create_tag("code", family="monospace")
        buffer.create_tag("pre", family="monospace", left_margin=12)
        buffer.create_tag("quote", left_margin=20, style=Pango.Style.ITALIC)
        buffer.create_tag("link", underline=Pango.Underline.SINGLE)
        for level, scale in enumerate((1.8, 1.5, 1.3, 1.15, 1.05, 1.0), 1):
            buffer.create_tag(f"h{level}", scale=scale, weight=Pango.Weight.BOLD)

    def render(self, source):
        parsed = parse_markdown(source)
        buffer = self.get_buffer()
        for widget in self.table_widgets:
            self.remove(widget)
        self.table_widgets.clear()
        buffer.set_text("")
        for text, styles in parsed.runs:
            start = buffer.get_char_count()
            if styles and styles[0].startswith("table:"):
                anchor = buffer.create_child_anchor(buffer.get_end_iter())
                grid = self.make_table(parsed.tables[int(styles[0].split(":")[1])])
                self.add_child_at_anchor(grid, anchor)
                self.table_widgets.append(grid)
            else:
                buffer.insert(buffer.get_end_iter(), text)
                for style in styles:
                    buffer.apply_tag_by_name(style, buffer.get_iter_at_offset(start),
                                             buffer.get_end_iter())

    @staticmethod
    def make_table(rows):
        grid = Gtk.Grid(column_homogeneous=False)
        cell_style = Gtk.CssProvider()
        cell_style.load_from_string(
            "frame { border-radius: 0; }"
            "frame.alternate-row { background-color: alpha(currentColor, 0.05); }")
        markup_tags = {"bold": "b", "italic": "i", "code": "tt"}
        for y, row in enumerate(rows):
            for x, (runs, header, align) in enumerate(row):
                parts = []
                for text, styles in runs:
                    text = escape(text)
                    for style in styles:
                        tag = markup_tags.get(style)
                        if tag:
                            text = f"<{tag}>{text}</{tag}>"
                    parts.append(text)
                markup = "".join(parts)
                if header:
                    markup = f"<b>{markup}</b>"
                justification = {0.0: Gtk.Justification.LEFT,
                                 0.5: Gtk.Justification.CENTER,
                                 1.0: Gtk.Justification.RIGHT}[align]
                label = Gtk.Label(xalign=align, justify=justification,
                                  hexpand=True, halign=Gtk.Align.FILL,
                                  yalign=0, selectable=True, wrap=True,
                                  wrap_mode=Pango.WrapMode.WORD_CHAR,
                                  max_width_chars=60, margin_start=10, margin_end=10,
                                  margin_top=8, margin_bottom=8)
                label.set_markup(markup)
                frame = Gtk.Frame()
                if not header and y % 2 == 0:
                    frame.add_css_class("alternate-row")
                frame.get_style_context().add_provider(
                    cell_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                frame.set_child(label)
                # TextView anchors allocate minimum widths, so reserve each
                # cell natural width rather than its one-character wrap minimum.
                _minimum, natural, _min_baseline, _nat_baseline = frame.measure(
                    Gtk.Orientation.HORIZONTAL, -1)
                frame.set_size_request(natural, -1)
                grid.attach(frame, x, y, 1, 1)
        return grid
