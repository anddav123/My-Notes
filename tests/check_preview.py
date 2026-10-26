"""GTK integration checks for live Markdown preview and tables."""
import time

from main import MyNotesApp, MyNotesWindow, Gio, GLib
from preview import parse_markdown


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        assert time.monotonic() < deadline, "Preview update timed out"
        GLib.MainContext.default().iteration(False)
        time.sleep(0.01)


source = """# Title

Hello **bold**, *italic* and `code` — café 👋.

- First
- Second

> Quoted text

```python
print('<hello>')
```

[GNOME](https://gnome.org) ![My image](missing.png)

| Item | Qty | Notes |
| :--- | ---: | :---: |
| **Pens** | 3 | *Blue* |
| Paper | 10 | `A4` |
"""
parsed = parse_markdown(source)
plain = "".join(text for text, _styles in parsed.runs)
assert "Title" in plain and "**bold**" not in plain
assert "• First" in plain and "print('<hello>')" in plain
assert "https://gnome.org" in plain and "[Image: My image]" in plain
assert any("h1" in styles for _text, styles in parsed.runs)
assert any("bold" in styles for _text, styles in parsed.runs)
assert len(parsed.tables) == 1 and len(parsed.tables[0]) == 3
table_source = "| Item | Quantity | Status |\n| :--- | ---: | :---: |\n| **Pens** | 3 | Ready |\n| Paper | 10 | Ordered |\n"
assert len(parse_markdown(table_source).tables) == 1
fenced = parse_markdown("```markdown\n" + table_source + "```\n")
assert not fenced.tables
assert "| **Pens** | 3 | Ready |" in "".join(t for t, _s in fenced.runs)
assert parsed.tables[0][0][0][1] is True
assert parsed.tables[0][1][1][2] == 1.0
assert parsed.tables[0][1][2][2] == 0.5
assert "bold" in parsed.tables[0][1][0][0][0][1]
assert "alert" not in "".join(t for t, _s in parse_markdown('<script>alert(1)</script>').runs)

app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
window = MyNotesWindow(app)
window.buffer.set_text(source)
wait(lambda: window.preview_timeout is None)
preview = window.preview.get_buffer()
assert "Title" in preview.get_text(*preview.get_bounds(), True)
assert len(window.preview.table_widgets) == 1
grid = window.preview.table_widgets[0]
from gi.repository import Gtk
for row in range(3):
    for column, alignment, justification in (
        (0, 0.0, Gtk.Justification.LEFT),
        (1, 1.0, Gtk.Justification.RIGHT),
        (2, 0.5, Gtk.Justification.CENTER),
    ):
        cell_label = grid.get_child_at(column, row).get_child()
        assert cell_label.get_xalign() == alignment
        assert cell_label.get_justify() == justification
        assert cell_label.get_hexpand()
assert grid.get_child_at(0, 0).get_child().get_text() == "Item"
assert grid.get_child_at(0, 1).get_child().get_text() == "Pens"
assert not window.preview.get_editable()
assert not window.preview_scroll.get_overlay_scrolling()
assert not window.panes.get_start_child().get_overlay_scrolling()
assert window.text() == source and window.buffer.get_modified()
assert window.lookup_action("preview").get_state().get_boolean()

window.lookup_action("preview").activate(None)
assert not window.preview_scroll.get_visible()
window.buffer.set_text("## Updated while hidden")
assert window.preview_timeout is None
window.lookup_action("preview").activate(None)
assert window.preview_scroll.get_visible()
assert "Updated while hidden" in preview.get_text(*preview.get_bounds(), True)
assert not window.preview.table_widgets
assert window.buffer.get_modified()

window.reset_document()
wait(lambda: window.preview_timeout is None)
assert preview.get_char_count() == 0 and not window.buffer.get_modified()
window.buffer.set_text("Pending update")
assert window.preview_timeout is not None
window.destroy()
wait(lambda: window.preview_timeout is None)
print("PASS: formatted Markdown, table cells/alignment, live updates, toggle, source preservation, cleanup")
