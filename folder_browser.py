"""Lazy local Markdown folder browser; never reads or writes note contents."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile

from gi.repository import Gio, GLib, Gtk, Pango

SCANS = ThreadPoolExecutor(max_workers=2, thread_name_prefix="note-folders")


def note_filename(value):
    name = value.strip()
    if (not name or name in (".", "..") or any(char in name for char in ("/", "\\"))
            or any(ord(char) < 32 or ord(char) == 127 for char in name)):
        raise ValueError("Enter a filename without folder separators or control characters.")
    if name.casefold() in (".md", ".markdown"):
        raise ValueError("Enter a name before the Markdown extension.")
    if not Path(name).suffix:
        name += ".md"
    if Path(name).suffix.casefold() not in (".md", ".markdown") or name.casefold() in (".md", ".markdown"):
        raise ValueError("Use a filename ending in .md or .markdown.")
    return name


class FolderState:
    def __init__(self, path):
        self.path = Path(path)
        self.folder = None
        self.visible = False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                folder = data.get("folder")
                if isinstance(folder, str) and Path(folder).is_absolute():
                    self.folder = folder
                    self.visible = data.get("visible") is True
        except (OSError, ValueError, UnicodeError):
            pass

    def save(self, folder, visible):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             delete=False) as stream:
                temporary = stream.name
                json.dump({"folder": folder, "visible": visible}, stream)
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        self.folder, self.visible = folder, visible


def scan_folder(path):
    entries = []
    with os.scandir(path) as iterator:
        for entry in iterator:
            # Do not follow directory symlinks, which can form cycles or leave
            # the chosen tree. Markdown symlink files can still be opened.
            directory = entry.is_dir(follow_symlinks=False)
            if directory or (Path(entry.name).suffix.casefold() in (".md", ".markdown")
                             and entry.is_file()):
                entries.append((directory, entry.name, entry.path))
    return sorted(entries, key=lambda item: (not item[0], item[1].casefold(), item[1]))


class FolderBrowser(Gtk.Box):
    def __init__(self, choose, open_file):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, width_request=220)
        self.open_file = open_file
        self.folder = None
        self.current = None
        self.expanded = set()
        self.buttons = {}
        self.monitors = []
        self.generation = 0
        self.pending = 0
        self.refresh_source = None
        self.closed = False
        top = Gtk.Box(spacing=6, margin_start=8, margin_end=8, margin_top=8)
        self.title = Gtk.Label(label="Notes folder", xalign=0, hexpand=True,
                               ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=24)
        top.append(self.title)
        self.new_button = Gtk.Button(icon_name="document-new-symbolic", tooltip_text="New note in this folder",
                                     action_name="win.new-in-folder", sensitive=False)
        top.append(self.new_button)
        change = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text="Choose notes folder")
        change.connect("clicked", lambda _button: choose())
        top.append(change)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh folder")
        refresh.connect("clicked", lambda _button: self.refresh())
        top.append(refresh)
        self.append(top)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                   overlay_scrolling=False)
        self.tree = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                            margin_start=8, margin_end=8, margin_bottom=8)
        scroll.set_child(self.tree)
        self.append(scroll)
        self.message(self.tree, "Choose a folder to browse Markdown notes.")

    @staticmethod
    def message(box, text):
        label = Gtk.Label(label=text, wrap=True, xalign=0, margin_top=8, margin_bottom=8)
        label.add_css_class("dim-label")
        box.append(label)

    def set_folder(self, folder):
        if folder != self.folder:
            self.expanded.clear()
        self.folder = folder
        self.new_button.set_sensitive(True)
        self.title.set_label(Path(folder).name or folder)
        self.title.set_tooltip_text(folder)
        self.refresh()

    def refresh(self):
        if self.closed or not self.folder:
            return
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
            self.refresh_source = None
        self.generation += 1
        for monitor in self.monitors:
            monitor.cancel()
        self.monitors.clear()
        self.buttons.clear()
        self.populate(self.tree, self.folder, self.generation)

    def changed(self, *_args):
        if self.closed or self.refresh_source:
            return
        def refresh():
            self.refresh_source = None
            self.refresh()
            return GLib.SOURCE_REMOVE
        self.refresh_source = GLib.timeout_add(250, refresh)

    def populate(self, box, path, generation):
        while box.get_first_child():
            box.remove(box.get_first_child())
        self.message(box, "Loading…")
        # Start the watch before scanning, so creations during a scan also
        # cause a refresh. Only expanded folders are scanned and watched.
        try:
            monitor = Gio.File.new_for_path(path).monitor_directory(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self.changed)
            self.monitors.append(monitor)
        except GLib.Error:
            pass  # Refresh remains available on filesystems without watches.
        self.pending += 1
        future = SCANS.submit(scan_folder, path)
        future.add_done_callback(lambda result: GLib.idle_add(self.scanned, box, generation, result))

    def scanned(self, box, generation, future):
        self.pending -= 1
        if self.closed or generation != self.generation:
            return GLib.SOURCE_REMOVE
        while box.get_first_child():
            box.remove(box.get_first_child())
        try:
            entries = future.result()
        except OSError as error:
            self.message(box, f"Could not read folder: {error.strerror or error}")
            return GLib.SOURCE_REMOVE
        if not entries:
            self.message(box, "No Markdown notes or subfolders")
        for directory, name, path in entries:
            if directory:
                expander = Gtk.Expander()
                label = Gtk.Label(label=name, xalign=0, ellipsize=Pango.EllipsizeMode.END,
                                  max_width_chars=24, tooltip_text=path)
                expander.set_label_widget(label)
                children = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_start=14)
                expander.set_child(children)
                loaded = [False]
                def expand(widget, _property, target=path, child=children, state=loaded):
                    if widget.get_expanded():
                        self.expanded.add(target)
                        if not state[0]:
                            state[0] = True
                            self.populate(child, target, generation)
                    else:
                        self.expanded.discard(target)
                expander.connect("notify::expanded", expand)
                box.append(expander)
                expander.set_expanded(path in self.expanded)
            else:
                button = Gtk.ToggleButton(tooltip_text=path)
                button.add_css_class("flat")
                row = Gtk.Box(spacing=6)
                row.append(Gtk.Image(icon_name="text-x-generic-symbolic"))
                row.append(Gtk.Label(label=name, xalign=0, hexpand=True,
                                     ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=24))
                button.set_child(row)
                button.update_property([Gtk.AccessibleProperty.LABEL], [name])
                self.buttons[path] = button
                button.set_active(path == self.current)
                button.connect("clicked", lambda _button, target=path: self.activate_file(target))
                box.append(button)
        return GLib.SOURCE_REMOVE

    def activate_file(self, path):
        # Selection reflects the loaded document, never a pending request.
        self.select(self.current)
        if path != self.current:
            self.open_file(Gio.File.new_for_path(path))

    def select(self, path):
        self.current = path
        for filename, button in self.buttons.items():
            button.set_active(filename == path)

    def cleanup(self):
        self.closed = True
        self.generation += 1
        if self.refresh_source:
            GLib.source_remove(self.refresh_source)
            self.refresh_source = None
        for monitor in self.monitors:
            monitor.cancel()
        self.monitors.clear()
