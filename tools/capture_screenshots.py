"""Render the real GTK app with isolated example notes and preferences."""
from pathlib import Path
import tempfile
from main import MyNotesApp, MyNotesWindow, Gtk, Gio, GLib

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/screenshots"
OUTPUT.mkdir(parents=True, exist_ok=True)
DEMO = """# Project notes

A simple place to plan, write and keep ideas.

## This week's checklist

- [x] Collect ideas
- [x] Draft the outline
- [ ] Share the finished notes

## Release plan

| Task | Owner | Status |
| :--- | :---: | --- |
| Write notes | Andrew | Complete |
| Review draft | Team | In progress |
| Publish | Andrew | Next |

## Useful details

Keep **important points** clear, add *a little emphasis*,
and use `inline code` when it helps.

> Good notes make it easier to pick up where you left off.

[Learn about CommonMark](https://commonmark.org)
"""

with tempfile.TemporaryDirectory(prefix="my-notes-screenshots-") as temporary:
    root = Path(temporary)
    notes = root / "Notes"
    notes.mkdir()
    (notes / "Ideas.md").write_text("# Ideas\n", encoding="utf-8")
    (notes / "Reading list.md").write_text("# Reading list\n", encoding="utf-8")
    project = notes / "Project notes.md"
    project.write_text(DEMO, encoding="utf-8")
    app = MyNotesApp(preferences_path=root / "preferences.json")
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    window = MyNotesWindow(app)
    window.set_default_size(1280, 820)
    window.folder_browser.set_folder(str(notes))
    window.folder_browser.set_visible(True)
    window.sidebar_action.set_state(GLib.Variant("b", True))
    window.file = Gio.File.new_for_path(str(project))
    window.buffer.set_text(DEMO)
    window.buffer.set_modified(False)
    window.refresh_preview()
    window.present()
    paintable = Gtk.WidgetPaintable.new(window)
    loop = GLib.MainLoop()

    def capture(name):
        snapshot = Gtk.Snapshot.new()
        paintable.snapshot(snapshot, window.get_width(), window.get_height())
        node = snapshot.to_node()
        if node is None:
            window.snapshot_child(window.get_child(), snapshot)
            node = snapshot.to_node()
        texture = window.get_renderer().render_texture(node, None)
        assert texture.save_to_png(str(OUTPUT / name))

    def preview():
        capture("preview.png")
        window.destroy()
        loop.quit()
        return GLib.SOURCE_REMOVE

    def split():
        if window.folder_browser.pending:
            return GLib.SOURCE_CONTINUE
        capture("editor-preview.png")
        window.folder_browser.set_visible(False)
        window.sidebar_action.set_state(GLib.Variant("b", False))
        window.set_view(False, True)
        GLib.timeout_add(800, preview)
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(1200, split)
    loop.run()
print(f"Screenshots: {OUTPUT}")
