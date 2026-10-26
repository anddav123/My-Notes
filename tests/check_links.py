"""Link resolution and GTK activation tests without launching external apps."""
import time

from links import resolve_link
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk
from gi.repository import Gdk
from preview import parse_markdown

base = "file:///home/andrew/Notes/My%20note.md"
assert resolve_link("https://example.org/a?q=1#part") == ("uri", "https://example.org/a?q=1#part")
assert resolve_link("mailto:hello@example.org")[0] == "uri"
assert resolve_link("//example.org/page")[1] == "https://example.org/page"
assert resolve_link("../Other/Read%20me.md", base)[1] == "file:///home/andrew/Other/Read%20me.md"
assert resolve_link("/tmp/example.md", base)[1] == "file:///tmp/example.md"
assert resolve_link("#hello%20world") == ("fragment", "hello world")
for bad in ("javascript:alert(1)", "data:text/html,hello", "shell:run", "https://", "https://bad\naddress"):
    try:
        resolve_link(bad, base)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid destination: {bad}")
try:
    resolve_link("relative.md")
except ValueError as error:
    assert "Save this note first" in str(error)
else:
    raise AssertionError("Unsaved note supplied a relative base")

source = '''# Links

[**Example**](https://example.org "Example title") and [reference][ref].

<mailto:hello@example.org>

[ref]: ../Other/Read%20me.md "Reference title"

| Link | Value |
| --- | --- |
| [Table link](https://example.org/table "Table title") | 1 |

## Second heading

## Second heading
'''
parsed = parse_markdown(source)
assert len(parsed.links) == 4
plain = "".join(t for t, _styles in parsed.runs)
assert "Example" in plain and "(https://example.org)" not in plain
assert any("bold" in styles and any(s.startswith("destination:") for s in styles)
           for _text, styles in parsed.runs)

app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
w.file = Gio.File.new_for_uri(base)
w.buffer.set_text(source)
w.refresh_preview()
w.present()
end = time.monotonic() + .6
while time.monotonic() < end:
    GLib.MainContext.default().iteration(False)
    time.sleep(.005)

opened, errors = [], []
w.launch_link = lambda kind, uri: opened.append((kind, uri))
w.error = lambda title, message: errors.append((title, str(message)))
preview = w.preview
buffer = preview.get_buffer()
text = buffer.get_text(*buffer.get_bounds(), True)
offset = text.index("Example")
iterator = buffer.get_iter_at_offset(offset)
assert preview.destination_at(iterator) == ("https://example.org", "Example title")
rect = preview.get_iter_location(iterator)
x, y = preview.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x + 3, rect.y + 3)
assert preview.destination_at_point(x, y)[0] == "https://example.org"
preview.link_motion(None, x, y)
assert preview.get_tooltip_text() == "Example title\nhttps://example.org"
preview.link_pressed(None, 1, x, y)
preview.link_released(None, 1, x, y)
assert opened == [("uri", "https://example.org")]

buffer.place_cursor(iterator)
assert preview.link_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType.CONTROL_MASK)
assert len(opened) == 2
preview.link_pressed(None, 1, x, y)
preview.link_released(None, 1, x + 10, y)
assert len(opened) == 2  # Drag selection must not open a link.
buffer.select_range(iterator, buffer.get_iter_at_offset(offset + 4))
preview.link_pressed(None, 1, x, y)
preview.link_released(None, 1, x, y)
assert len(opened) == 2
buffer.place_cursor(iterator)

table_label = preview.table_widgets[0].get_child_at(0, 1).get_child()
assert table_label.get_text() == "Table link"
assert table_label.emit("activate-link", "https://example.org/table")
assert opened[-1] == ("uri", "https://example.org/table")
w.open_preview_link(preview, "../Other/Read%20me.md")
assert opened[-1] == ("file", "file:///home/andrew/Other/Read%20me.md")
assert preview.scroll_to_heading("second-heading")
assert preview.scroll_to_heading("second-heading-1")
assert not preview.scroll_to_heading("missing")
w.open_preview_link(preview, "#missing")
assert errors[-1][0] == "Heading not found"
w.file = None
w.open_preview_link(preview, "relative.md")
assert "Save this note first" in errors[-1][1]
before = len(opened)
w.open_preview_link(preview, "javascript:alert(1)")
assert len(opened) == before
assert w.text() == source and w.buffer.get_modified()

# Replacing the note must remove obsolete destinations and their text tags.
old_names = list(preview.link_tags)
preview.render("No links")
assert not preview.links and not preview.link_tags
assert all(buffer.get_tag_table().lookup(name) is None for name in old_names)
w.destroy()
print("PASS: link text/titles, reference/mail/table links, coordinate click, keyboard, drag/selection, relative paths, heading fragments, invalid schemes, cleanup")
