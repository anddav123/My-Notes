"""Saved GFM mode, legacy settings, live multiwindow preference updates."""
import json
from pathlib import Path
import tempfile
import time
from preferences import ButtonPreferences
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk

def settle():
    end = time.monotonic() + .15
    while time.monotonic() < end:
        GLib.MainContext.default().iteration(False)
        time.sleep(.005)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'preferences.json'
    path.write_text('{"button_style":"icons"}')
    prefs = ButtonPreferences(path)
    assert prefs.button_style == 'icons' and prefs.gfm_enabled
    prefs.set_gfm_enabled(False)
    loaded = ButtonPreferences(path)
    assert loaded.button_style == 'icons' and not loaded.gfm_enabled
    prefs.set_button_style('text')
    assert not ButtonPreferences(path).gfm_enabled
    app = MyNotesApp(preferences_path=path)
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    w, second = MyNotesWindow(app), MyNotesWindow(app)
    source = '- [x] Done\n\n~~Removed~~\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n'
    for window in (w, second):
        window.buffer.set_text(source)
        window.buffer.set_modified(False)
        window.refresh_preview()
        assert not window.gfm_action.get_state().get_boolean()
        assert not window.preview.task_widgets and not window.preview.table_widgets
    w.present()
    w.show_preferences()
    settle()
    assert w.gfm_row.get_title() == 'GitHub Flavoured Markdown (GFM)'
    assert not w.gfm_row.get_active()
    w.gfm_row.set_active(True)
    for window in (w, second):
        assert window.gfm_action.get_state().get_boolean()
        assert len(window.preview.task_widgets) == 1
        assert len(window.preview.table_widgets) == 1
        assert window.status.get_text().startswith('GFM')
        assert window.text() == source and not window.buffer.get_modified()
    assert ButtonPreferences(path).gfm_enabled
    w.button_style_row.set_selected(1)
    assert ButtonPreferences(path).button_style == 'icons'
    assert ButtonPreferences(path).gfm_enabled
    w.gfm_row.set_active(False)
    assert not ButtonPreferences(path).gfm_enabled
    assert ButtonPreferences(path).button_style == 'icons'
    assert not second.preview.task_widgets

    def walk(widget):
        yield widget
        child = widget.get_first_child()
        while child:
            yield from walk(child)
            child = child.get_next_sibling()

    for button in walk(w):
        if isinstance(button, Gtk.MenuButton) and button.get_menu_model():
            model = button.get_menu_model()
            for i in range(model.get_n_items()):
                action = model.get_item_attribute_value(i, 'action', None)
                assert not action or action.get_string() != 'win.gfm'
    w.preferences_dialog.close()
    settle()
    assert w.gfm_row is None
    second.destroy()
    w.destroy()
    for value in ('"false"', '0', 'null'):
        path.write_text('{"button_style":"text","gfm_enabled":' + value + '}')
        assert ButtonPreferences(path).gfm_enabled
    print('PASS: legacy migration, persisted GFM, live Preferences switch, multiwindow mode refresh, independent toolbar setting, clean notes, menu removal, invalid-value fallback')
