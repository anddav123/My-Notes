"""Creation must never overwrite files or bypass unsaved-change protection."""
import tempfile
import time
from pathlib import Path
from main import MyNotesApp, MyNotesWindow, Gio, GLib
from folder_browser import note_filename


def wait(predicate):
    deadline = time.monotonic() + 5
    while True:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        if predicate():
            return
        if time.monotonic() > deadline:
            raise AssertionError("Timed out")
        time.sleep(.01)


assert note_filename(" Café ") == "Café.md"
assert note_filename("Notes.MARKDOWN") == "Notes.MARKDOWN"
for bad in ("", " ", ".", "..", "../escape", "/absolute", "a/b", "a\\b", "bad\x00.md", "bad\n.md", "a.txt", ".md"):
    try:
        note_filename(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    notes = root / "notes"
    notes.mkdir()
    app = MyNotesApp(preferences_path=root / "preferences.json")
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    window = MyNotesWindow(app)
    window.present()
    browser = window.folder_browser
    browser.set_folder(str(notes))
    browser.set_visible(True)
    wait(lambda: browser.pending == 0)

    def prompt(name, response="create"):
        window.new_folder_note()
        dialog = window.get_visible_dialog()
        assert dialog and window.busy
        entry = dialog.get_extra_child().get_first_child()
        assert not dialog.get_response_enabled("create")
        entry.set_text(name)
        assert dialog.get_response_enabled("create")
        dialog.emit("response", response)

    prompt("Cancelled", "cancel")
    assert not window.busy and not (notes / "Cancelled.md").exists()
    prompt("Café")
    wait(lambda: not window.busy and browser.pending == 0)
    created = notes / "Café.md"
    assert created.exists() and created.read_bytes() == b""
    assert window.file.get_path() == str(created) and not window.buffer.get_modified()
    assert browser.buttons[str(created)].get_active()
    assert app.recent_notes.uris[0] == created.as_uri()

    window.buffer.set_text("Keep my edits")
    prompt("Second")
    assert window.get_visible_dialog().get_heading() == "Save changes?"
    window.get_visible_dialog().emit("response", "cancel")
    assert not (notes / "Second.md").exists()
    assert window.text() == "Keep my edits" and browser.current == str(created)
    prompt("Second")
    window.get_visible_dialog().emit("response", "save")
    wait(lambda: not window.busy and window.file.get_basename() == "Second.md")
    assert created.read_text() == "Keep my edits" and window.text() == ""
    window.buffer.set_text("Discard these")
    prompt("Third.markdown")
    window.get_visible_dialog().emit("response", "discard")
    wait(lambda: not window.busy and window.file.get_basename() == "Third.markdown")
    assert (notes / "Second.md").read_bytes() == b""

    errors = []
    window.error = lambda title, error: errors.append((title, str(error)))
    prompt("Café")
    wait(lambda: not window.busy)
    assert errors and created.read_text() == "Keep my edits"
    assert window.file.get_basename() == "Third.markdown"
    # An existing symlink also fails exclusive creation, preserving its target.
    (notes / "link.md").symlink_to(created)
    prompt("link.md")
    wait(lambda: not window.busy)
    assert len(errors) == 2 and created.read_text() == "Keep my edits"

    # A failed save must prevent creation and keep the current document dirty.
    current = notes / "Third.markdown"
    current.unlink()
    current.mkdir()
    window.buffer.set_text("Must stay here")
    prompt("Blocked")
    window.get_visible_dialog().emit("response", "save")
    wait(lambda: not window.busy)
    assert not (notes / "Blocked.md").exists()
    assert window.text() == "Must stay here" and window.buffer.get_modified()
    # Creation in a disappeared folder reports an error without switching.
    missing = Gio.File.new_for_path(str(root / "missing" / "No.md"))
    window.create_folder_note(missing)
    wait(lambda: not window.busy)
    assert window.text() == "Must stay here" and window.buffer.get_modified()
    window.destroy()
print("PASS: filename validation, extension, Unicode, cancel, exclusive creation, sidebar selection, recent history, Save/Discard/Cancel, existing-file/symlink protection, failed-save and missing-folder safety")
