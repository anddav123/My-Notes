"""Exercise recent history, popover and safe async opening in a real GTK session."""
import tempfile
import time
from pathlib import Path
from main import MyNotesApp, MyNotesWindow, GLib, Gio, Gtk
from recent_notes import RecentNotes


def spin(test=lambda: True):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        if test():
            return
        time.sleep(.01)
    raise AssertionError("Timed out")


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    history = RecentNotes(root / "history.json")
    files = []
    for number in range(12):
        path = root / f"Note {number}.md"
        path.write_text(f"# Note {number}\nCafé", encoding="utf-8")
        file = Gio.File.new_for_path(str(path))
        history.add(file)
        files.append(file)
    assert len(history.uris) == 5
    history.add(files[4])
    assert history.uris[0] == files[4].get_uri() and len(history.uris) == 5
    assert RecentNotes(history.path).uris == history.uris
    history.remove(files[4].get_uri())
    assert (root / "Note 4.md").exists()
    assert files[4].get_uri() not in RecentNotes(history.path).uris
    history.path.write_text("{broken", encoding="utf-8")
    assert RecentNotes(history.path).uris == []
    app = MyNotesApp(preferences_path=root / "preferences.json")
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    window = MyNotesWindow(app)
    window.present()
    window.open_recent(files[2])
    spin(lambda: not window.busy)
    assert window.text() == "# Note 2\nCafé"
    assert app.recent_notes.uris == [files[2].get_uri()]
    window.open_button.popup()
    spin()
    popover = window.recent_popover
    assert popover.matches == app.recent_notes.uris
    popover.search.set_text("NOte 2")
    popover.refresh()
    assert len(popover.matches) == 1
    popover.search.set_text("does not match")
    popover.refresh()
    assert popover.empty.get_visible() and not popover.matches
    popover.search.set_text("")
    popover.refresh()
    popover.popdown()
    window.buffer.insert_at_cursor(" unsaved")
    original = window.text()
    window.open_recent(files[3])
    spin()
    dialog = window.get_visible_dialog()
    assert dialog and window.busy
    dialog.emit("response", "cancel")
    spin(lambda: not window.busy)
    assert window.text() == original and window.buffer.get_modified()
    assert app.recent_notes.uris == [files[2].get_uri()]
    window.open_recent(files[3])
    spin()
    window.get_visible_dialog().emit("response", "discard")
    spin(lambda: not window.busy and window.file.equal(files[3]))
    assert window.text() == "# Note 3\nCafé" and not window.buffer.get_modified()
    errors = []
    window.error = lambda title, error: errors.append(title)
    window.open_recent(Gio.File.new_for_path(str(root / "missing.md")))
    spin(lambda: not window.busy)
    assert errors == ["Could not open note"]
    assert window.file.equal(files[3]) and window.text() == "# Note 3\nCafé"
    assert len(app.recent_notes.uris) == 2
    app.preferences.set_button_style("icons")
    assert window.open_button.get_icon_name() == "document-open-symbolic"
    app.preferences.set_button_style("text")
    assert window.open_button.get_label() == "Open"
    window.set_busy(True)
    assert not window.open_button.get_sensitive()
    window.set_busy(False)
    window.destroy()
print("PASS: five-file limit, ordering, deduplication, persistence, corrupt history, removal without deletion, search, icon/text styles, cancel/discard protection, missing-file safety")

