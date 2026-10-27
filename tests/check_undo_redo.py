"""Undo/redo controls, edit grouping, mode switching and history boundaries."""
from pathlib import Path
import tempfile
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib


def settle():
    end = time.monotonic() + .25
    while time.monotonic() < end:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)


with tempfile.TemporaryDirectory() as directory:
    app = MyNotesApp(preferences_path=Path(directory) / 'settings.json')
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    w = MyNotesWindow(app)
    w.present()
    settle()

    def note(text):
        w.focus_document()
        w.find_bar.close(focus_editor=False)
        w.buffer.begin_irreversible_action()
        w.buffer.set_text(text)
        w.buffer.end_irreversible_action()
        w.buffer.set_modified(False)
        w.buffer.place_cursor(w.buffer.get_end_iter())
        w.focus_document()

    def append(text):
        w.buffer.begin_user_action()
        w.buffer.insert(w.buffer.get_end_iter(), text)
        w.buffer.end_user_action()

    note('Alpha')
    undo, redo = w.lookup_action('undo'), w.lookup_action('redo')
    assert not undo.get_enabled() and not redo.get_enabled()
    append(' beta')
    assert undo.get_enabled() and not redo.get_enabled()
    undo.activate(None)
    assert w.text() == 'Alpha'
    assert not undo.get_enabled() and redo.get_enabled()
    redo.activate(None)
    assert w.text() == 'Alpha beta'
    assert undo.get_enabled() and not redo.get_enabled()
    undo.activate(None)
    append(' gamma')
    assert w.text() == 'Alpha gamma' and not redo.get_enabled()

    # An edit undone from Preview-only becomes visible in the editor.
    w.set_view(False, True)
    undo.activate(None)
    assert w.text() == 'Alpha'
    assert w.editor_scroll.get_visible() and w.preview_scroll.get_visible()
    redo.activate(None)
    assert w.text() == 'Alpha gamma'
    settle()
    p = w.preview.get_buffer()
    assert 'Alpha gamma' in p.get_text(*p.get_bounds(), True)

    w.set_busy(True)
    assert not undo.get_enabled() and not redo.get_enabled()
    w.undo_redo(False)
    assert w.text() == 'Alpha gamma'
    w.set_busy(False)
    assert undo.get_enabled()

    note('cat cat cat')
    w.open_find(True)
    w.find_bar.find_entry.set_text('cat')
    w.find_bar.replace_entry.set_text('dog')
    w.find_bar.refresh(select=True)
    assert w.find_bar.replace_all() == 3
    assert w.text() == 'dog dog dog'
    # Focused search entries must not redirect their own Undo into the note.
    w.find_bar.find_entry.grab_focus()
    before = w.text()
    w.undo_redo(False)
    assert w.text() == before
    w.editor.grab_focus()
    undo.activate(None)
    assert w.text() == 'cat cat cat'
    redo.activate(None)
    assert w.text() == 'dog dog dog'

    # Saving retains the note's undo history.
    w.file = Gio.File.new_for_path(str(Path(directory) / 'saved.md'))
    w.etag = None
    w.save_document()
    deadline = time.monotonic() + 5
    while w.busy and time.monotonic() < deadline:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)
    assert not w.busy and not w.buffer.get_modified() and undo.get_enabled()
    w.editor.grab_focus()
    undo.activate(None)
    assert w.text() == 'cat cat cat' and w.buffer.get_modified()
    redo.activate(None)
    assert w.text() == 'dog dog dog'

    w.reset_document()
    assert not undo.get_enabled() and not redo.get_enabled()
    assert not w.buffer.get_modified()
    assert app.get_accels_for_action('win.undo') == ['<Control>z']
    assert set(app.get_accels_for_action('win.redo')) == {'<Shift><Control>z', '<Control>y'}
    w.destroy()
print('PASS: dynamic Undo/Redo, shortcuts, redo invalidation, preview-only activation, live preview, busy guard, search-field isolation, grouped replacement, save history, new-document boundary')
