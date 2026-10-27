"""Preference persistence and live toolbar styling checks with isolated settings."""
import json
from pathlib import Path
import tempfile
import time

from preferences import ButtonPreferences
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk


def settle():
    end = time.monotonic() + .2
    while time.monotonic() < end:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)


with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'settings' / 'preferences.json'
    prefs = ButtonPreferences(path)
    assert prefs.button_style == 'text'
    assert not path.exists()
    prefs.set_button_style('icons')
    assert json.loads(path.read_text()) == {'button_style': 'icons', 'gfm_enabled': True}
    assert ButtonPreferences(path).button_style == 'icons'
    assert not list(path.parent.glob('*.tmp'))
    prefs.set_button_style('text')

    app = MyNotesApp(preferences_path=path)
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    w = MyNotesWindow(app)
    note = '# Keep this note\n\nUnsaved text stays here.'
    w.buffer.set_text(note)
    w.present()
    settle()
    assert len(w.styled_buttons) == 5
    assert all(button.get_label() == label for button, label, _icon in w.styled_buttons)
    w.show_preferences()
    settle()
    dialog = w.preferences_dialog
    assert w.button_style_row.get_selected() == 0
    w.show_preferences()
    assert w.preferences_dialog is dialog
    w.button_style_row.set_selected(1)
    settle()
    theme = Gtk.IconTheme.get_for_display(w.get_display())
    for button, label, icon in w.styled_buttons:
        assert theme.has_icon(icon), f'Theme does not contain {icon}'
        assert button.get_icon_name() == icon
        assert button.get_tooltip_text()
        assert button.get_action_name().startswith('win.')
    assert ButtonPreferences(path).button_style == 'icons'
    assert w.text() == note and w.buffer.get_modified()

    # A second window follows changes immediately and future windows load them.
    second = MyNotesWindow(app)
    assert all(button.get_icon_name() == icon for button, _label, icon in second.styled_buttons)
    w.lookup_action('editor').activate(None)
    assert not w.editor_scroll.get_visible() and w.preview_scroll.get_visible()
    w.button_style_row.set_selected(0)
    settle()
    assert not w.editor_scroll.get_visible() and w.preview_scroll.get_visible()
    for window in (w, second):
        assert all(button.get_label() == label for button, label, _icon in window.styled_buttons)
    assert ButtonPreferences(path).button_style == 'text'
    assert w.text() == note and w.buffer.get_modified()
    dialog.close()
    settle()
    assert w.preferences_dialog is None
    second.destroy()
    w.destroy()

    for bad in ('not JSON', '[]', '{"button_style":"unknown"}'):
        path.write_text(bad)
        assert ButtonPreferences(path).button_style == 'text'
    blocked = Path(directory) / 'not-a-directory'
    blocked.write_text('test')
    prefs = ButtonPreferences(blocked / 'preferences.json')
    try:
        prefs.set_button_style('icons')
    except OSError:
        assert prefs.button_style == 'text'
    else:
        raise AssertionError('Failed persistence was not reported')
print('PASS: text/icons, GNOME icon availability, live settings dialog, persistence, multiwindow updates, pane/source preservation, malformed settings and write failures')
