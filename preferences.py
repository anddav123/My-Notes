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
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("button_style") in ("text", "icons"):
                self._button_style = data["button_style"]
        except (OSError, ValueError, UnicodeError):
            pass  # Missing or malformed settings fall back to the normal toolbar.

    @GObject.Property(type=str, default="text", flags=GObject.ParamFlags.READABLE)
    def button_style(self):
        return self._button_style

    def set_button_style(self, style):
        if style not in ("text", "icons"):
            raise ValueError("Unknown button style.")
        if style == self._button_style:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="preferences-", suffix=".tmp", delete=False) as stream:
                temp_path = Path(stream.name)
                json.dump({"button_style": style}, stream)
                stream.write("\n")
            os.replace(temp_path, self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
        self._button_style = style
        self.notify("button-style")
