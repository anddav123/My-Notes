"""Find/replace regression tests with temporary settings and in-memory notes."""
from pathlib import Path
import tempfile
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gdk


def settle(seconds=.2):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)


with tempfile.TemporaryDirectory() as directory:
    app = MyNotesApp(preferences_path=Path(directory) / 'preferences.json')
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    w = MyNotesWindow(app)
    w.present()
    settle()
    bar = w.find_bar

    def note(text):
        w.focus_document()
        bar.close(focus_editor=False)
        w.buffer.begin_irreversible_action()
        w.buffer.set_text(text)
        w.buffer.end_irreversible_action()
        w.buffer.set_modified(False)
        w.buffer.place_cursor(w.buffer.get_start_iter())
        w.refresh_preview()

    def query(text, case=False, replace=False):
        w.open_find(replace)
        bar.match_case.set_active(case)
        bar.find_entry.set_text(text)
        bar.refresh(select=True)

    original = 'Cat cat 🐈 cat.\nCAFÉ café.\n'
    note(original)
    w.set_view(False, True)
    w.lookup_action('find').activate(None)
    assert w.editor_scroll.get_visible() and w.preview_scroll.get_visible()
    assert bar.get_visible() and not bar.replace_row.get_visible()
    focus = w.get_focus()
    assert focus == bar.find_entry or focus.is_ancestor(bar.find_entry)
    query('cat')
    assert len(bar.matches) == 3
    assert [original[start:end] for start, end in bar.matches] == ['Cat', 'cat', 'cat']
    assert bar.count_label.get_text() == '1 of 3'
    assert not w.buffer.get_modified() and not w.save_button.has_css_class('suggested-action')
    assert not w.buffer.get_can_undo()
    for count in (2, 3, 1):
        w.lookup_action('find-next').activate(None)
        assert bar.count_label.get_text() == f'{count} of 3'
    w.lookup_action('find-previous').activate(None)
    assert bar.count_label.get_text() == '3 of 3'
    bar.match_case.set_active(True)
    assert len(bar.matches) == 2
    query('café')
    assert len(bar.matches) == 2
    bar.match_case.set_active(True)
    assert len(bar.matches) == 1
    query('🐈')
    assert len(bar.matches) == 1
    query('missing')
    assert not bar.matches and bar.count_label.get_text() == '0 matches'
    assert not bar.next_button.get_sensitive()
    query('')
    assert not bar.matches and bar.count_label.get_text() == ''
    assert not w.buffer.get_modified()

    note(original)
    query('cat', replace=True)
    bar.replace_entry.set_text('catfish')
    assert bar.replace_current() == 1
    assert w.text() == 'catfish cat 🐈 cat.\nCAFÉ café.\n'
    assert w.buffer.get_modified() and w.save_button.has_css_class('suggested-action')
    # Replacement selects the following match, not the match inside catfish.
    assert bar.selection_offsets()[0] == len('catfish ')
    w.buffer.undo()
    assert w.text() == original
    settle()
    query('cat', replace=True)
    bar.replace_entry.set_text('dog')
    assert bar.replace_all() == 3
    replaced = 'dog dog 🐈 dog.\nCAFÉ café.\n'
    assert w.text() == replaced
    w.buffer.undo()
    assert w.text() == original
    w.buffer.redo()
    assert w.text() == replaced
    settle(.25)
    preview_text = w.preview.get_buffer()
    assert 'dog dog 🐈 dog.' in preview_text.get_text(*preview_text.get_bounds(), True)

    note('aaaaa')
    query('aa', replace=True)
    assert bar.matches == [(0, 2), (2, 4)]
    bar.replace_entry.set_text('b')
    assert bar.replace_all() == 2 and w.text() == 'bba'
    w.buffer.undo()
    assert w.text() == 'aaaaa'

    note('a.b a?b a.b')
    query('a.b', replace=True)
    bar.replace_entry.set_text(r'$1\path')
    assert bar.replace_all() == 2
    assert w.text() == r'$1\path a?b $1\path'

    note('🍎 🍎')
    query('🍎', replace=True)
    bar.replace_entry.set_text('')
    assert bar.replace_all() == 2 and w.text() == ' '
    w.buffer.undo()
    assert w.text() == '🍎 🍎'

    note('one one')
    query('one', replace=True)
    bar.replace_entry.set_text('two')
    w.set_busy(True)
    assert bar.replace_all() == 0 and w.text() == 'one one'
    assert not w.lookup_action('find-replace').get_enabled()
    w.set_busy(False)
    assert w.lookup_action('find-replace').get_enabled()
    bar.replace_entry.grab_focus()
    settle(.05)
    assert bar.key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
    # Disabling editing cleared the old selection; first Enter selects safely.
    if w.text() == 'one one':
        assert bar.key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
    assert w.text() == 'two one'
    assert bar.key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0))
    assert not bar.get_visible() and not bar.matches

    w.set_view(False, True)
    w.lookup_action('find-replace').activate(None)
    assert w.editor_scroll.get_visible() and w.preview_scroll.get_visible()
    assert bar.replace_row.get_visible()
    w.set_view(False, True)
    assert not bar.get_visible()
    w.open_find()
    w.reset_document()
    bar.refresh()
    assert not bar.matches and not w.buffer.get_can_undo()
    assert not w.buffer.get_modified()
    w.destroy()
print('PASS: preview-only activation/focus, match counts/wrap/case/Unicode, literal replacement/deletion, one-step undo/redo, live preview, busy protection, keyboard controls, document reset')
