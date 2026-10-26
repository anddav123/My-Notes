"""My Notes: a small GTK4 Markdown source editor."""
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk
from preview import MarkdownPreview
from links import resolve_link


class MyNotesWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="My Notes")
        self.set_default_size(1000, 700)
        self.file = None
        self.etag = None
        self.busy = False
        self.allow_close = False
        self.preview_timeout = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="Untitled", subtitle="My Notes")
        header.set_title_widget(self.title_widget)
        for label, action in (("New", "new"), ("Open", "open")):
            header.pack_start(Gtk.Button(label=label, action_name=f"win.{action}"))
        header.pack_end(Gtk.Button(label="Save", action_name="win.save"))
        menu = Gio.Menu()
        menu.append("Save As…", "win.save-as")
        menu.append("Show Preview", "win.preview")
        menu.append("Enable GitHub Flavored Markdown (GFM)", "win.tables")
        self.tables_action = Gio.SimpleAction.new_stateful("tables", None, GLib.Variant("b", True))
        self.tables_action.connect("activate", self.toggle_tables)
        self.add_action(self.tables_action)
        self.preview_action = Gio.SimpleAction.new_stateful("preview", None, GLib.Variant("b", True))
        self.preview_action.connect("activate", self.toggle_preview)
        self.add_action(self.preview_action)
        app.set_accels_for_action("win.preview", ["<primary><shift>p"])
        header.pack_end(Gtk.ToggleButton(label="Preview", action_name="win.preview"))
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        toolbar.add_top_bar(header)

        self.buffer = Gtk.TextBuffer()
        self.editor = Gtk.TextView(
            buffer=self.buffer, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=24, right_margin=24, top_margin=24, bottom_margin=24,
            hexpand=True, vexpand=True,
        )
        self.editor.update_property([Gtk.AccessibleProperty.LABEL], ["Markdown editor"])
        # GTK 4.18 overlay scrollbars can lose their allocation during live
        # text reflow. Conventional scrollbars avoid that snapshot race.
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True, overlay_scrolling=False)
        scroll.set_child(self.editor)
        self.preview = MarkdownPreview()
        self.preview.connect("link-activated", self.open_preview_link)
        self.preview_scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True,
                                                overlay_scrolling=False)
        self.preview_scroll.set_child(self.preview)
        self.panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.panes.set_start_child(scroll)
        self.panes.set_end_child(self.preview_scroll)
        self.panes.set_resize_start_child(True)
        self.panes.set_resize_end_child(True)
        self.panes.set_shrink_start_child(False)
        self.panes.set_shrink_end_child(False)
        self.panes.set_position(500)
        self.status = Gtk.Label(xalign=1, margin_start=12, margin_end=12,
                                margin_top=6, margin_bottom=6)
        self.status.add_css_class("dim-label")
        toolbar.add_bottom_bar(self.status)
        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(self.panes)
        toolbar.set_content(self.toasts)
        self.set_content(toolbar)

        for name, callback, shortcuts in (
            ("new", self.new_document, ["<primary>n"]),
            ("open", self.open_document, ["<primary>o"]),
            ("save", self.save_document, ["<primary>s"]),
            ("save-as", lambda: self.save_document(save_as=True), ["<primary><shift>s"]),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, cb=callback: cb())
            self.add_action(action)
            app.set_accels_for_action(f"win.{name}", shortcuts)
        self.buffer.connect("changed", self.update_status)
        self.buffer.connect("modified-changed", self.update_status)
        self.buffer.connect("changed", self.schedule_preview)
        self.connect("destroy", self.cleanup_preview)
        self.connect("close-request", self.on_close_request)
        self.update_status()
        self.refresh_preview()

    def toggle_preview(self, action, _parameter):
        visible = not action.get_state().get_boolean()
        action.set_state(GLib.Variant("b", visible))
        self.preview_scroll.set_visible(visible)
        if visible:
            self.refresh_preview()

    def toggle_tables(self, action, _parameter):
        action.set_state(GLib.Variant("b", not action.get_state().get_boolean()))
        if self.preview_scroll.get_visible():
            self.refresh_preview()

    def schedule_preview(self, *_args):
        self.cleanup_preview()
        if self.preview_scroll.get_visible():
            self.preview_timeout = GLib.timeout_add(200, self.refresh_preview)

    def cleanup_preview(self, *_args):
        if self.preview_timeout is not None:
            GLib.source_remove(self.preview_timeout)
            self.preview_timeout = None

    def refresh_preview(self):
        self.cleanup_preview()
        self.preview.render(self.text(), tables=self.tables_action.get_state().get_boolean())
        return GLib.SOURCE_REMOVE

    def text(self):
        return self.buffer.get_text(*self.buffer.get_bounds(), True)

    def open_preview_link(self, _preview, destination):
        try:
            kind, uri = resolve_link(destination, self.file.get_uri() if self.file else None)
            if kind == "fragment":
                if not self.preview.scroll_to_heading(uri):
                    self.error("Heading not found", "There is no matching heading in this note.")
                return
            self.launch_link(kind, uri)
        except ValueError as error:
            self.error("Could not open link", error)

    def launch_link(self, kind, uri):
        launcher = (Gtk.FileLauncher(file=Gio.File.new_for_uri(uri)) if kind == "file"
                    else Gtk.UriLauncher(uri=uri))

        def launched(source, result):
            try:
                source.launch_finish(result)
            except GLib.Error as error:
                if not error.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                    self.error("Could not open link", error.message)

        launcher.launch(self, None, launched)

    def update_status(self, *_args):
        name = self.file.get_basename() if self.file else "Untitled"
        self.title_widget.set_title(f"{'• ' if self.buffer.get_modified() else ''}{name}")
        self.set_title(f"{name} — My Notes")
        text = self.text()
        self.status.set_text(f"Markdown  ·  {len(text.split())} words  ·  {len(text)} characters")

    def set_busy(self, busy):
        self.busy = busy
        self.editor.set_editable(not busy)
        for name in ("new", "open", "save", "save-as"):
            self.lookup_action(name).set_enabled(not busy)

    def error(self, heading, message):
        dialog = Adw.AlertDialog(heading=heading, body=str(message))
        dialog.add_response("close", "Close")
        dialog.set_close_response("close")
        dialog.present(self)

    def confirm_changes(self, continuation):
        if self.busy:
            return
        if not self.buffer.get_modified():
            continuation()
            return
        self.set_busy(True)
        dialog = Adw.AlertDialog(heading="Save changes?",
                                body="Your note has unsaved changes.")
        for response, label in (("cancel", "Cancel"), ("discard", "Discard"), ("save", "Save")):
            dialog.add_response(response, label)
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def respond(_dialog, response):
            self.set_busy(False)
            if response == "discard":
                continuation()
            elif response == "save":
                self.save_document(after_save=continuation)

        dialog.connect("response", respond)
        dialog.present(self)

    def new_document(self):
        self.confirm_changes(self.reset_document)

    def reset_document(self):
        self.file = None
        self.etag = None
        self.buffer.set_text("")
        self.buffer.set_modified(False)
        self.update_status()
        self.editor.grab_focus()

    def file_dialog(self, title):
        markdown = Gtk.FileFilter(name="Markdown and text")
        for pattern in ("*.md", "*.markdown", "*.txt"):
            markdown.add_pattern(pattern)
        all_files = Gtk.FileFilter(name="All files")
        all_files.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(markdown)
        filters.append(all_files)
        return Gtk.FileDialog(title=title, filters=filters, default_filter=markdown)

    def dialog_error(self, error):
        if not (error.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED)
                or error.matches(Gtk.dialog_error_quark(), Gtk.DialogError.CANCELLED)):
            self.error("File selection failed", error.message)

    def open_document(self):
        self.confirm_changes(self.choose_open)

    def choose_open(self):
        self.set_busy(True)
        self.file_dialog("Open note").open(self, None, self.open_selected)

    def open_selected(self, dialog, result):
        try:
            selected = dialog.open_finish(result)
        except GLib.Error as error:
            self.set_busy(False)
            self.dialog_error(error)
            return
        selected.load_contents_async(None, self.loaded)

    def loaded(self, selected, result):
        try:
            _success, contents, etag = selected.load_contents_finish(result)
            text = contents.decode("utf-8")
            # Gtk.TextBuffer cannot preserve embedded NUL characters.
            if "\x00" in text:
                raise ValueError("This file contains NUL characters and cannot be edited as text.")
        except (GLib.Error, UnicodeError, ValueError) as error:
            self.set_busy(False)
            self.error("Could not open note", error)
            return
        self.file, self.etag = selected, etag
        self.buffer.set_text(text)
        self.buffer.set_modified(False)
        self.set_busy(False)
        self.update_status()
        self.editor.grab_focus()

    def save_document(self, save_as=False, after_save=None):
        if self.busy:
            return
        self.set_busy(True)
        if self.file is not None and not save_as:
            self.write_file(self.file, after_save)
            return
        dialog = self.file_dialog("Save note")
        if self.file:
            dialog.set_initial_file(self.file)
        else:
            dialog.set_initial_name("Untitled.md")

        def selected(chooser, result):
            try:
                target = chooser.save_finish(result)
            except GLib.Error as error:
                self.set_busy(False)
                self.dialog_error(error)
                return
            self.write_file(target, after_save)

        dialog.save(self, None, selected)

    def write_file(self, target, after_save=None):
        etag = self.etag if self.file and target.equal(self.file) else None

        def saved(file, result):
            try:
                _success, new_etag = file.replace_contents_finish(result)
            except GLib.Error as error:
                self.set_busy(False)
                self.error("Could not save note", error)
                return
            self.file, self.etag = file, new_etag
            self.buffer.set_modified(False)
            self.set_busy(False)
            self.update_status()
            self.toasts.add_toast(Adw.Toast(title="Note saved"))
            if after_save:
                after_save()

        contents = GLib.Bytes.new(self.text().encode("utf-8"))
        target.replace_contents_bytes_async(contents, etag, False,
                                            Gio.FileCreateFlags.NONE, None, saved)

    def on_close_request(self, *_args):
        if self.allow_close:
            return False

        def close():
            self.allow_close = True
            self.close()

        self.confirm_changes(close)
        return True


class MyNotesApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.anddav.MyNotes")

    def do_activate(self):
        window = self.props.active_window or MyNotesWindow(self)
        window.present()
        window.editor.grab_focus()


if __name__ == "__main__":
    sys.exit(MyNotesApp().run(sys.argv))
