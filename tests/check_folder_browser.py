"""Folder browsing and protected file-switching checks in a real GTK session."""
import tempfile
import time
from pathlib import Path
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk
from folder_browser import FolderState, scan_folder


def wait(predicate):
    deadline = time.monotonic() + 6
    while True:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        if predicate():
            return
        if time.monotonic() > deadline:
            raise AssertionError("Timed out")
        time.sleep(.01)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    notes = root / "Notes"
    notes.mkdir()
    sub = notes / "Nested"
    sub.mkdir()
    first, second, third = notes / "A.md", notes / "B.MARKDOWN", sub / "C.md"
    for path in (first, second, third):
        path.write_text(path.stem, encoding="utf-8")
    (notes / "ignore.txt").write_text("ignore")
    (notes / "loop").symlink_to(notes, target_is_directory=True)
    entries = scan_folder(notes)
    assert [item[1] for item in entries] == ["Nested", "A.md", "B.MARKDOWN"]
    app = MyNotesApp(preferences_path=root / "preferences.json")
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    window = MyNotesWindow(app)
    window.present()
    browser = window.folder_browser
    browser.set_folder(str(notes))
    browser.set_visible(True)
    window.sidebar_action.set_state(GLib.Variant("b", True))
    window.save_folder_state()
    wait(lambda: browser.pending == 0)
    assert set(browser.buttons) == {str(first), str(second)}
    expander = browser.tree.get_first_child()
    assert isinstance(expander, Gtk.Expander)
    expander.set_expanded(True)
    wait(lambda: browser.pending == 0)
    assert str(third) in browser.buttons
    browser.buttons[str(first)].emit("clicked")
    wait(lambda: not window.busy)
    assert window.text() == "A" and browser.buttons[str(first)].get_active()
    window.buffer.insert_at_cursor(" edited")
    edited = window.text()
    browser.buttons[str(second)].emit("clicked")
    wait(lambda: window.get_visible_dialog() is not None)
    assert browser.buttons[str(first)].get_active()
    assert not browser.buttons[str(second)].get_active()
    window.get_visible_dialog().emit("response", "cancel")
    wait(lambda: not window.busy)
    assert window.text() == edited and browser.current == str(first)
    browser.activate_file(str(second))
    wait(lambda: window.get_visible_dialog() is not None)
    window.get_visible_dialog().emit("response", "save")
    wait(lambda: not window.busy and window.file.get_path() == str(second))
    assert first.read_text() == edited and window.text() == "B"
    assert browser.buttons[str(second)].get_active()
    window.buffer.insert_at_cursor(" discard me")
    browser.activate_file(str(third))
    wait(lambda: window.get_visible_dialog() is not None)
    window.get_visible_dialog().emit("response", "discard")
    wait(lambda: not window.busy and window.file.get_path() == str(third))
    assert second.read_text() == "B" and browser.current == str(third)
    errors = []
    window.error = lambda title, error: errors.append(title)
    browser.activate_file(str(notes / "missing.md"))
    wait(lambda: not window.busy)
    assert errors == ["Could not open note"]
    assert browser.current == str(third) and window.text() == "C"
    # File monitoring updates the tree, retaining expansion and selection.
    added = notes / "new.md"
    added.write_text("new")
    wait(lambda: str(added) in browser.buttons and browser.pending == 0)
    assert str(third) in browser.buttons and browser.buttons[str(third)].get_active()
    added.unlink()
    wait(lambda: str(added) not in browser.buttons and browser.pending == 0)
    window.toggle_sidebar(None, None)
    assert not browser.get_visible()
    state = FolderState(app.folder_state.path)
    assert state.folder == str(notes) and not state.visible
    window.toggle_sidebar(None, None)
    assert browser.get_visible()
    restored = MyNotesApp(preferences_path=root / "preferences.json")
    assert restored.folder_state.folder == str(notes) and restored.folder_state.visible
    # Missing remembered folders display an inline error without losing a note.
    browser.set_folder(str(root / "gone"))
    wait(lambda: browser.pending == 0)
    assert "Could not read folder" in browser.tree.get_first_child().get_label()
    assert window.text() == "C"
    window.destroy()
    assert browser.closed and not browser.monitors
print("PASS: Markdown filtering, sorting, lazy subfolders, symlink cycles, selection, Cancel/Save/Discard, failed-open safety, live updates, sidebar toggle, per-user restoration and missing folders")
