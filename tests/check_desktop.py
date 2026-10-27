"""Validate per-user launcher installation without touching real user entries."""
import importlib.util
from pathlib import Path
import tempfile
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gio, GdkPixbuf, Gtk, Gdk
from main import MyNotesApp

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_desktop", ROOT / "tools/install_desktop.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
with tempfile.TemporaryDirectory() as directory:
    data_home = Path(directory)
    launcher = installer.install(data_home, refresh=False)
    app_info = Gio.DesktopAppInfo.new_from_filename(str(launcher))
    assert app_info and app_info.get_name() == "My Notes"
    assert app_info.get_executable() == "/usr/bin/sh"
    assert str(ROOT / "run.sh") in app_info.get_commandline()
    assert app_info.get_icon().to_string() == installer.APP_ID
    assert not app_info.get_boolean("Terminal")
    icon = data_home / f"icons/hicolor/scalable/apps/{installer.APP_ID}.svg"
    assert icon.read_bytes() == (ROOT / f"data/icons/hicolor/scalable/apps/{installer.APP_ID}.svg").read_bytes()
    for size in (32, 48, 128):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon), size, size, True)
        assert pixbuf.get_width() == size and pixbuf.get_height() == size
    original = launcher.read_text()
    installer.install(data_home, refresh=False)
    assert launcher.read_text() == original
    launcher.write_text("[Desktop Entry]\nName=Custom launcher\n")
    try:
        installer.install(data_home, refresh=False)
    except FileExistsError:
        assert "Custom launcher" in launcher.read_text()
    else:
        raise AssertionError("Unmanaged launcher was overwritten")

app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
assert Gtk.Window.get_default_icon_name() == installer.APP_ID
theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
assert theme.has_icon(installer.APP_ID)
print("PASS: launcher metadata, venv wrapper, installed SVG at 32/48/128px, safe reinstall, unmanaged-entry protection, app icon identity")
