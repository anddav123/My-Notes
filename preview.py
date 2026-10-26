"""Render Markdown as native GTK text, tables, links, and images."""
from html.parser import HTMLParser
from html import escape
import re

from markdown_engine import render_markdown
from images import PreviewImage
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, Gdk, GObject


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
        self.links = {}
        self.images = {}

    def add(self, text):
        if text:
            styles = tuple(self.STYLES[tag] for tag, _attrs in self.stack if tag in self.STYLES)
            styles += tuple(attrs["_link"] for tag, attrs in self.stack
                            if tag == "a" and "_link" in attrs)
            styles += tuple(attrs["key"] for tag, attrs in self.stack if tag == "image-marker")
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
        if tag == "a" and "href" in attrs:
            key = f"destination:{len(self.links)}"
            self.links[key] = (attrs["href"], attrs.get("title", ""))
            attrs["_link"] = key
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
            try:
                start = int(attrs.get("start", "1")) if tag == "ol" else 1
            except ValueError:
                start = 1
            self.lists.append([tag, start - 1])
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
            key = f"image:{len(self.images)}"
            self.images[key] = (attrs.get("src", ""), attrs.get("alt", ""), attrs.get("title", ""))
            self.stack.append(("image-marker", {"key": key}))
            self.add(f"[Image: {attrs.get('alt') or 'image'}]")
            self.stack.pop()
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
        if not any(tag in ("pre", "code") for tag, _attrs in self.stack):
            # Ignore the HTML serializer's whitespace between block elements.
            if data.isspace() and "\n" in data:
                return
            data = re.sub(r"[ \t\n\r\f]+", " ", data)
        self.add(data)


def parse_markdown(source, *, tables=True):
    parser = MarkdownText()
    parser.feed(render_markdown(source, tables=tables))
    parser.close()
    return parser


class MarkdownPreview(Gtk.TextView):
    __gsignals__ = {"link-activated": (GObject.SignalFlags.RUN_LAST, None, (str,))}

    def __init__(self):
        super().__init__(editable=False, cursor_visible=True,
                         wrap_mode=Gtk.WrapMode.WORD_CHAR,
                         left_margin=24, right_margin=24, top_margin=24, bottom_margin=24,
                         hexpand=True, vexpand=True)
        self.update_property([Gtk.AccessibleProperty.LABEL], ["Markdown preview"])
        self.table_widgets = []
        self.image_widgets = []
        self.inline_images = []
        self.remote_images_allowed = set()
        self.document_uri = None
        self.images = {}
        self.connect("destroy", self.cleanup_images)
        self.link_tags = {}
        self.links = {}
        self.press_position = None
        click = Gtk.GestureClick(button=1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", self.link_pressed)
        click.connect("released", self.link_released)
        self.add_controller(click)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.link_motion)
        motion.connect("leave", self.link_leave)
        self.add_controller(motion)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.link_key_pressed)
        self.add_controller(keys)
        buffer = self.get_buffer()
        buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        buffer.create_tag("italic", style=Pango.Style.ITALIC)
        buffer.create_tag("code", family="monospace")
        buffer.create_tag("pre", family="monospace", left_margin=12)
        buffer.create_tag("quote", left_margin=20, style=Pango.Style.ITALIC)
        buffer.create_tag("link", underline=Pango.Underline.SINGLE)
        for level, scale in enumerate((1.8, 1.5, 1.3, 1.15, 1.05, 1.0), 1):
            buffer.create_tag(f"h{level}", scale=scale, weight=Pango.Weight.BOLD)

    def destination_at(self, iterator):
        for tag in iterator.get_tags():
            name = tag.get_property("name")
            if name in self.links:
                return self.links[name]
        return None

    def destination_at_point(self, x, y):
        bx, by = self.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        on_text, iterator = self.get_iter_at_location(bx, by)
        return self.destination_at(iterator) if on_text else None

    def link_pressed(self, _gesture, _count, x, y):
        self.press_position = (x, y)

    def link_released(self, _gesture, count, x, y):
        pressed, self.press_position = self.press_position, None
        if count != 1 or pressed is None or self.get_buffer().get_has_selection():
            return
        if abs(x - pressed[0]) > 5 or abs(y - pressed[1]) > 5:
            return
        destination = self.destination_at_point(x, y)
        if destination:
            self.emit("link-activated", destination[0])

    def link_motion(self, _controller, x, y):
        destination = self.destination_at_point(x, y)
        self.set_cursor_from_name("pointer" if destination else "text")
        self.set_tooltip_text("\n".join(filter(None, (destination[1], destination[0]))) if destination else None)

    def link_leave(self, _controller):
        self.set_cursor_from_name("text")
        self.set_tooltip_text(None)

    def link_key_pressed(self, _controller, keyval, _keycode, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and state & Gdk.ModifierType.CONTROL_MASK:
            buffer = self.get_buffer()
            destination = self.destination_at(buffer.get_iter_at_mark(buffer.get_insert()))
            if destination:
                self.emit("link-activated", destination[0])
                return True
        return False

    def table_link_activated(self, _label, href):
        self.emit("link-activated", href)
        return True  # Always handle here; never let Gtk.Label launch implicitly.

    def scroll_to_heading(self, fragment):
        buffer = self.get_buffer()
        if not fragment:
            self.scroll_to_iter(buffer.get_start_iter(), 0.0, True, 0.0, 0.0)
            return True
        counts = {}
        for line in range(buffer.get_line_count()):
            _found, start = buffer.get_iter_at_line(line)
            if not any((tag.get_property("name") or "") in ("h1", "h2", "h3", "h4", "h5", "h6")
                       for tag in start.get_tags()):
                continue
            end = start.copy()
            end.forward_to_line_end()
            text = buffer.get_text(start, end, True)
            slug = re.sub(r"[^\w\s-]", "", text.lower())
            slug = re.sub(r"\s+", "-", slug.strip())
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            unique = slug + (f"-{count}" if count else "")
            if unique == fragment:
                self.scroll_to_iter(start, 0.1, True, 0.0, 0.0)
                return True
        return False

    def cleanup_images(self, *_args):
        for image in self.image_widgets:
            image.detach()
        self.image_widgets.clear()

    def make_image(self, key, styles, *, in_table=False):
        source, alt, title = self.images[key]
        width = min(480, max(120, self.get_width() - 48)) if self.get_width() else 480
        image = PreviewImage(source, alt, title, self.document_uri,
                             self.remote_images_allowed,
                             max_width=160 if in_table else width,
                             max_height=120 if in_table else 320)
        self.image_widgets.append(image)
        destination = next((self.links[s][0] for s in styles if s in self.links), None)
        if destination is not None:
            button = Gtk.Button(halign=Gtk.Align.START)
            image.remove(image.picture)
            button.set_child(image.picture)
            button.set_has_frame(False)
            image.picture.bind_property("visible", button, "visible", GObject.BindingFlags.SYNC_CREATE)
            button.set_tooltip_text(destination)
            button.connect("clicked", lambda _button: self.emit("link-activated", destination))
            image.prepend(button)
            image.link_button = button
        return image

    def render(self, source, *, tables=True, document_uri=None):
        parsed = parse_markdown(source, tables=tables)
        self.cleanup_images()
        self.images = parsed.images
        self.document_uri = document_uri
        buffer = self.get_buffer()
        for widget in self.inline_images:
            self.remove(widget)
        self.inline_images.clear()
        for widget in self.table_widgets:
            self.remove(widget)
        self.table_widgets.clear()
        buffer.set_text("")
        for tag in self.link_tags.values():
            buffer.get_tag_table().remove(tag)
        self.link_tags.clear()
        self.links = parsed.links
        for name in self.links:
            self.link_tags[name] = buffer.create_tag(name)
        self.link_leave(None)
        for text, styles in parsed.runs:
            start = buffer.get_char_count()
            image_key = next((s for s in styles if s in self.images), None)
            if image_key is not None:
                anchor = buffer.create_child_anchor(buffer.get_end_iter())
                widget = self.make_image(image_key, styles)
                self.add_child_at_anchor(widget, anchor)
                self.inline_images.append(widget)
                for style in styles:
                    if style in self.links:
                        buffer.apply_tag_by_name(style, buffer.get_iter_at_offset(start),
                                                 buffer.get_end_iter())
            elif styles and styles[0].startswith("table:"):
                anchor = buffer.create_child_anchor(buffer.get_end_iter())
                grid = self.make_table(parsed.tables[int(styles[0].split(":")[1])])
                self.add_child_at_anchor(grid, anchor)
                self.table_widgets.append(grid)
            else:
                buffer.insert(buffer.get_end_iter(), text)
                for style in styles:
                    buffer.apply_tag_by_name(style, buffer.get_iter_at_offset(start),
                                             buffer.get_end_iter())

    def make_table(self, rows):
        grid = Gtk.Grid(column_homogeneous=False)
        cell_style = Gtk.CssProvider()
        cell_style.load_from_string(
            "frame { border-radius: 0; }"
            "frame.alternate-row { background-color: alpha(currentColor, 0.05); }")
        for y, row in enumerate(rows):
            for x, (runs, header, align) in enumerate(row):
                image_runs = any(s in self.images for _text, styles in runs for s in styles)
                if image_runs:
                    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                                      margin_start=10, margin_end=10, margin_top=8, margin_bottom=8)
                    text_runs = []
                    for text, styles in runs:
                        key = next((s for s in styles if s in self.images), None)
                        if key:
                            if text_runs:
                                content.append(self.cell_label(text_runs, header, align))
                                text_runs = []
                            content.append(self.make_image(key, styles, in_table=True))
                        else:
                            text_runs.append((text, styles))
                    if text_runs:
                        content.append(self.cell_label(text_runs, header, align))
                else:
                    content = self.cell_label(runs, header, align)
                frame = Gtk.Frame()
                if not header and y % 2 == 0:
                    frame.add_css_class("alternate-row")
                frame.get_style_context().add_provider(
                    cell_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                frame.set_child(content)
                # TextView anchors allocate minimum widths, so reserve each
                # cell natural width rather than its one-character wrap minimum.
                _minimum, natural, _min_baseline, _nat_baseline = frame.measure(
                    Gtk.Orientation.HORIZONTAL, -1)
                frame.set_size_request(natural, -1)
                grid.attach(frame, x, y, 1, 1)
        return grid

    def cell_label(self, runs, header, align):
        markup_tags = {"bold": "b", "italic": "i", "code": "tt"}
        parts = []
        for text, styles in runs:
            text = escape(text)
            for style in styles:
                tag = markup_tags.get(style)
                if tag:
                    text = f"<{tag}>{text}</{tag}>"
                elif style in self.links:
                    href, title = self.links[style]
                    title_attr = f' title="{escape(title, quote=True)}"' if title else ""
                    text = f'<a href="{escape(href, quote=True)}"{title_attr}>{text}</a>'
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
        label.connect("activate-link", self.table_link_activated)
        return label
