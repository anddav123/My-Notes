from pathlib import Path
import tempfile
"""Check actual table allocations in a displayed GTK window."""
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib
from gi.repository import Gtk

test_preferences = tempfile.TemporaryDirectory(prefix="my-notes-test-")
app = MyNotesApp(preferences_path=Path(test_preferences.name) / "preferences.json")
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
window = MyNotesWindow(app)
window.buffer.set_text('''| Item | Quantity | Status |
| :--- | ---: | :---: |
| **Pens** | 3 | Ready |
| Paper | 10 | Ordered |
''')
window.present()
deadline = time.monotonic() + 1.5
while time.monotonic() < deadline:
    GLib.MainContext.default().iteration(False)
    time.sleep(.01)
grid = window.preview.table_widgets[0]
widths = []
for column in range(3):
    frame = grid.get_child_at(column, 0)
    label = frame.get_child()
    widths.append(frame.get_width())
    layout = label.get_layout()
    assert layout.get_line_count() == 1, (label.get_text(), label.get_width())
    assert label.get_width() > 20
    assert frame.get_width() >= frame.get_size_request()[0] - 2
assert len(set(widths)) > 1, widths
assert grid.get_child_at(0, 1).get_child().get_layout().get_line_count() == 1
print('PASS: displayed headers and short cells stay on one line; content-based column widths:', widths)
window.destroy()
