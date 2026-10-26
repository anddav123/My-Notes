"""Verify linked pane controls and displayed one/two-pane layouts."""
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk


def settle():
    deadline = time.monotonic() + .25
    while time.monotonic() < deadline:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)


app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
note = '# Modes\n\nSome **formatted** text.\n'
w.buffer.set_text(note)
w.buffer.set_modified(False)
w.refresh_preview()
w.present()
settle()


def buttons(widget):
    result = []
    if isinstance(widget, Gtk.ToggleButton) and widget.get_label() in ('Editor', 'Preview'):
        result.append(widget)
    child = widget.get_first_child()
    while child:
        result.extend(buttons(child))
        child = child.get_next_sibling()
    return result


controls = {button.get_label(): button for button in buttons(w)}
assert set(controls) == {'Editor', 'Preview'}


def check(editor, preview):
    settle()
    assert w.editor_scroll.get_visible() == editor
    assert w.preview_scroll.get_visible() == preview
    assert w.editor_action.get_state().get_boolean() == editor
    assert w.preview_action.get_state().get_boolean() == preview
    assert controls['Editor'].get_active() == editor
    assert controls['Preview'].get_active() == preview
    assert editor or preview
    assert w.text() == note and not w.buffer.get_modified()


check(True, True)
w.panes.set_position(360)
settle()
divider = w.panes.get_position()
controls['Preview'].emit('clicked')
check(True, False)
assert w.editor_scroll.get_width() >= w.panes.get_width() - 2
# Clicking the only active control must not leave a blank window.
controls['Editor'].emit('clicked')
check(True, False)
controls['Preview'].emit('clicked')
check(True, True)
assert abs(w.panes.get_position() - divider) <= 1
controls['Editor'].emit('clicked')
check(False, True)
assert w.preview_scroll.get_width() >= w.panes.get_width() - 2
controls['Preview'].emit('clicked')
check(False, True)

# Keyboard cycling reaches each of the three valid states.
w.lookup_action('cycle-view').activate(None)
check(True, True)
w.lookup_action('cycle-view').activate(None)
check(True, False)
w.lookup_action('cycle-view').activate(None)
check(False, True)

# Showing a stale hidden preview refreshes it without changing the source.
w.set_view(True, False)
w.buffer.set_text('# Updated while hidden')
assert w.preview_timeout is None
w.set_view(False, True)
text = w.preview.get_buffer()
assert 'Updated while hidden' in text.get_text(*text.get_bounds(), True)
assert w.buffer.get_modified()
w.destroy()
print('PASS: actual linked-button states, editor/split/preview widths, no blank state, divider restoration, three-mode shortcut, hidden-preview refresh, source preservation')
