"""Integration checks, run on the VM with its GTK display."""
import pathlib
import tempfile
import time

from main import MyNotesApp, MyNotesWindow, Gio, GLib


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("Async operation timed out")
        GLib.MainContext.default().iteration(False)
        time.sleep(0.01)


app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
window = MyNotesWindow(app)
errors = []
window.error = lambda heading, body: errors.append((heading, str(body)))
with tempfile.TemporaryDirectory() as directory:
    path = pathlib.Path(directory) / "note.md"
    file = Gio.File.new_for_path(str(path))
    note = "# My note\n\nHello **Markdown** — café 👋\n"
    window.buffer.set_text(note)
    assert window.buffer.get_modified()
    assert "•" in window.title_widget.get_title()
    window.set_busy(True)
    window.write_file(file)
    wait(lambda: not window.busy)
    assert not errors, errors
    assert path.read_text() == note
    assert not window.buffer.get_modified()
    assert window.file.equal(file)

    window.reset_document()
    assert window.text() == "" and window.file is None
    window.set_busy(True)
    file.load_contents_async(None, window.loaded)
    wait(lambda: not window.busy)
    assert window.text() == note

    # An external update must not be overwritten by a stale editor save.
    time.sleep(0.05)
    path.write_text("External edit, preserve this")
    window.buffer.set_text("Local edit")
    window.save_document()
    wait(lambda: not window.busy)
    assert errors and path.read_text() == "External edit, preserve this"
    assert window.buffer.get_modified()
    errors.clear()

    # Invalid text must leave the existing buffer and document identity intact.
    invalid = pathlib.Path(directory) / "invalid.md"
    for content in (b"\xff\xfe", b"hello\x00world"):
        invalid.write_bytes(content)
        window.set_busy(True)
        Gio.File.new_for_path(str(invalid)).load_contents_async(None, window.loaded)
        wait(lambda: not window.busy)
        assert errors and window.text() == "Local edit" and window.file.equal(file)
        errors.clear()

    called = []
    window.confirm_changes(lambda: called.append(True))
    assert window.busy
    window.get_visible_dialog().emit("response", "cancel")
    assert not window.busy and not called
    window.confirm_changes(lambda: called.append(True))
    window.get_visible_dialog().emit("response", "discard")
    assert called and not window.busy

    # Saving during a destructive action resumes it only after successful I/O.
    window.file = Gio.File.new_for_path(str(pathlib.Path(directory) / "second.md"))
    window.etag = None
    called.clear()
    window.confirm_changes(lambda: called.append(True))
    window.get_visible_dialog().emit("response", "save")
    wait(lambda: not window.busy)
    assert called and not window.buffer.get_modified()
    assert window.file.load_contents(None)[1] == b"Local edit"

window.destroy()
print("PASS: UTF-8 round trip, modified state, external edit conflict, invalid text, cancel/discard/save protection")
