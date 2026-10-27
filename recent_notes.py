"""Private recent-file history and a searchable Open popover."""
import json
import os
from pathlib import Path
import tempfile

from gi.repository import Gio, GLib, GObject, Gtk


class RecentNotes(GObject.Object):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, path=None):
        super().__init__()
        self.path = Path(path) if path else Path(GLib.get_user_state_dir()) / "MyNotes/recent-notes.json"
        self.uris = []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for uri in data:
                    if isinstance(uri, str) and Gio.File.new_for_uri(uri).get_path() and uri not in self.uris:
                        self.uris.append(uri)
                self.uris = self.uris[:5]
        except (OSError, ValueError):
            pass

    def update(self, uris):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             delete=False) as stream:
                temporary = stream.name
                json.dump(uris, stream, ensure_ascii=False)
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        self.uris = uris
        self.emit("changed")

    def add(self, file):
        # Only local files: history must not cause remote connections.
        if file.get_path():
            uri = file.get_uri()
            self.update(([uri] + [old for old in self.uris if old != uri])[:5])

    def remove(self, uri):
        self.update([old for old in self.uris if old != uri])


class RecentPopover(Gtk.Popover):
    def __init__(self, history, open_file, browse, report_error):
        super().__init__()
        self.history, self.open_file, self.report_error = history, open_file, report_error
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)
        top = Gtk.Box(spacing=6)
        self.search = Gtk.SearchEntry(hexpand=True, placeholder_text="Search recent notes")
        self.search.update_property([Gtk.AccessibleProperty.LABEL], ["Search recent notes"])
        top.append(self.search)
        folder = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text="Browse for a note")
        folder.connect("clicked", lambda _button: (self.popdown(), browse()))
        top.append(folder)
        box.append(top)
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                   min_content_width=320, max_content_height=350,
                                   propagate_natural_height=True)
        scroll.set_child(self.list)
        box.append(scroll)
        self.empty = Gtk.Label(label="No recent notes", margin_top=18, margin_bottom=18)
        self.empty.add_css_class("dim-label")
        box.append(self.empty)
        self.set_child(box)
        self.search.connect("search-changed", self.refresh)
        self.search.connect("activate", self.activate_first)
        self.search.connect("stop-search", lambda _entry: self.popdown())
        self.handler = history.connect("changed", self.refresh)
        self.connect("notify::visible", self.shown)
        self.refresh()

    def shown(self, *_args):
        if self.get_visible():
            self.search.set_text("")
            self.refresh()
            self.search.grab_focus()

    def refresh(self, *_args):
        while self.list.get_first_child():
            self.list.remove(self.list.get_first_child())
        self.matches = []
        query = self.search.get_text().casefold().strip()
        for uri in self.history.uris:
            file = Gio.File.new_for_uri(uri)
            path = Path(file.get_path())
            name, folder = path.name, str(path.parent)
            home = str(Path.home())
            if folder == home or folder.startswith(home + os.sep):
                folder = "~" + folder[len(home):]
            if query and query not in (name + " " + folder).casefold():
                continue
            self.matches.append(uri)
            row = Gtk.Box(spacing=6)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            from gi.repository import Pango
            for text, dim in ((name, False), (folder, True)):
                label = Gtk.Label(label=text, xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE,
                                  max_width_chars=36)
                if dim:
                    label.add_css_class("dim-label")
                    label.add_css_class("caption")
                labels.append(label)
            button = Gtk.Button(child=labels, hexpand=True, tooltip_text=str(path))
            button.add_css_class("flat")
            button.connect("clicked", lambda _button, value=uri: self.select(value))
            row.append(button)
            remove = Gtk.Button(icon_name="window-close-symbolic", valign=Gtk.Align.CENTER,
                                tooltip_text=f"Remove {name} from recent notes")
            remove.add_css_class("flat")
            remove.connect("clicked", lambda _button, value=uri: self.remove(value))
            row.append(remove)
            self.list.append(row)
        self.empty.set_label("No matching notes" if query else "No recent notes")
        self.empty.set_visible(not self.matches)
        self.list.set_visible(bool(self.matches))

    def select(self, uri):
        self.popdown()
        self.open_file(Gio.File.new_for_uri(uri))

    def activate_first(self, *_args):
        if self.matches:
            self.select(self.matches[0])

    def remove(self, uri):
        try:
            self.history.remove(uri)
        except OSError as error:
            self.report_error("Could not update recent notes", error)

    def cleanup(self):
        self.history.disconnect(self.handler)
