"""Small, atomic per-user preference store, independent of note files."""
import json
import os
from pathlib import Path
import tempfile

from gi.repository import GLib, GObject


class ButtonPreferences(GObject.Object):
    def __init__(self, path=None):
        super().__init__()
        self.path = Path(path) if path else Path(GLib.get_user_config_dir()) / "MyNotes" / "preferences.json"
        self._button_style = "text"
        self._gfm_enabled = True
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("button_style") in ("text", "icons"):
                self._button_style = data["button_style"]
            if isinstance(data, dict) and isinstance(data.get("gfm_enabled"), bool):
                self._gfm_enabled = data["gfm_enabled"]
        except (OSError, ValueError, UnicodeError):
            pass  # Missing or malformed settings fall back to the normal toolbar.

    @GObject.Property(type=str, default="text", flags=GObject.ParamFlags.READABLE)
    def button_style(self):
        return self._button_style

    @GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READABLE)
    def gfm_enabled(self):
        return self._gfm_enabled

    def set_button_style(self, style):
        if style not in ("text", "icons"):
            raise ValueError("Unknown button style.")
        if style == self._button_style:
            return
        self.save(style, self._gfm_enabled)
        self._button_style = style
        self.notify("button-style")

    def set_gfm_enabled(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("GFM preference must be true or false.")
        if enabled == self._gfm_enabled:
            return
        self.save(self._button_style, enabled)
        self._gfm_enabled = enabled
        self.notify("gfm-enabled")

    def save(self, button_style, gfm_enabled):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="preferences-", suffix=".tmp", delete=False) as stream:
                temp_path = Path(stream.name)
                json.dump({"button_style": button_style, "gfm_enabled": gfm_enabled}, stream)
                stream.write("\n")
            os.replace(temp_path, self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
