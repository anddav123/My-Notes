"""My Notes: a small GTK4 Markdown source editor."""
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gio, GLib, Gtk, Gdk
from preview import MarkdownPreview
from links import resolve_link
from preferences import ButtonPreferences
from find_replace import FindReplaceBar
from recent_notes import RecentNotes, RecentPopover
from folder_browser import FolderBrowser, FolderState, note_filename


class MyNotesWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="My Notes")
        self.set_default_size(1000, 700)
        self.file = None
        self.etag = None
        self.busy = False
        self.allow_close = False
        self.preview_timeout = None
        self.split_position = 500
        self.styled_buttons = []
        self.preferences_dialog = None
        self.button_style_row = None
        self.gfm_row = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="Untitled", subtitle="My Notes")
        header.set_title_widget(self.title_widget)
        self.file_controls = Gtk.Box()
        self.file_controls.add_css_class("linked")
        for label, icon, action in (("New", "document-new-symbolic", "new"),
                                    ("Open", "document-open-symbolic", "open"),
                                    ("Save", "media-floppy-symbolic", "save")):
            if action == "open":
                button = Gtk.MenuButton(label=label, tooltip_text="Open a recent note or browse")
                button.set_always_show_arrow(True)
                button.update_property([Gtk.AccessibleProperty.LABEL], [label])
                self.styled_buttons.append((button, label, icon))
                self.open_button = button
                self.recent_popover = RecentPopover(app.recent_notes, self.open_recent,
                                                    self.open_document, self.error)
                button.set_popover(self.recent_popover)
                self.connect("destroy", lambda _window: self.recent_popover.cleanup())
            else:
                button = self.toolbar_button(label, icon, action)
            self.file_controls.append(button)
            if action == "save":
                self.save_button = button
        menu = Gio.Menu()
        menu.append("Open Folder…", "win.open-folder")
        menu.append("New Note in Folder…", "win.new-in-folder")
        menu.append("Save As…", "win.save-as")
        for label, action, shortcut in (("Undo", "win.undo", "<primary>z"),
                                         ("Redo", "win.redo", "<primary><shift>z")):
            item = Gio.MenuItem.new(label, action)
            item.set_attribute_value("accel", GLib.Variant("s", shortcut))
            menu.append_item(item)
        menu.append("Find…", "win.find")
        menu.append("Find and Replace…", "win.find-replace")
        menu.append("Preferences", "win.preferences")
        self.gfm_action = Gio.SimpleAction.new_stateful("gfm", None, GLib.Variant("b", app.preferences.gfm_enabled))
        self.gfm_action.connect("activate", self.toggle_gfm)
        self.add_action(self.gfm_action)
        self.preview_action = Gio.SimpleAction.new_stateful("preview", None, GLib.Variant("b", True))
        self.preview_action.connect("activate", self.toggle_pane)
        self.add_action(self.preview_action)
        self.editor_action = Gio.SimpleAction.new_stateful("editor", None, GLib.Variant("b", True))
        self.editor_action.connect("activate", self.toggle_pane)
        self.add_action(self.editor_action)
        cycle = Gio.SimpleAction.new("cycle-view", None)
        cycle.connect("activate", self.cycle_view)
        self.add_action(cycle)
        app.set_accels_for_action("win.cycle-view", ["<primary><shift>p"])
        self.sidebar_action = Gio.SimpleAction.new_stateful("sidebar", None,
                                                          GLib.Variant("b", app.folder_state.visible))
        self.sidebar_action.connect("activate", self.toggle_sidebar)
        self.add_action(self.sidebar_action)
        app.set_accels_for_action("win.sidebar", ["F9"])
        header.pack_start(self.toolbar_button("Folders", "sidebar-show-symbolic", "sidebar", toggle=True))
        header.pack_start(self.file_controls)
        view_controls = Gtk.Box()
        view_controls.add_css_class("linked")
        view_controls.append(self.toolbar_button("Editor", "document-edit-symbolic", "editor", toggle=True))
        view_controls.append(self.toolbar_button("Preview", "view-reveal-symbolic", "preview", toggle=True))
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        header.pack_end(view_controls)
        toolbar.add_top_bar(header)

        self.buffer = Gtk.TextBuffer(enable_undo=True)
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
        self.editor_scroll = scroll
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
        self.folder_browser = FolderBrowser(self.choose_folder, self.open_recent)
        self.folder_browser.set_visible(app.folder_state.visible)
        self.browser_panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.browser_panes.set_start_child(self.folder_browser)
        self.browser_panes.set_end_child(self.panes)
        self.browser_panes.set_resize_start_child(False)
        self.browser_panes.set_shrink_start_child(False)
        self.browser_panes.set_shrink_end_child(False)
        self.browser_panes.set_position(250)
        self.toasts.set_child(self.browser_panes)
        toolbar.set_content(self.toasts)
        self.set_content(toolbar)
        self.find_bar = FindReplaceBar(self.editor)
        self.find_bar.connect("replaced", lambda _bar, count: self.toasts.add_toast(
            Adw.Toast(title=f"Replaced {count} match" if count == 1 else f"Replaced {count} matches")))
        toolbar.add_top_bar(self.find_bar)

        for name, callback, shortcuts in (
            ("new", self.new_document, ["<primary>n"]),
            ("open", self.open_document, ["<primary>o"]),
            ("open-folder", self.choose_folder, ["<primary><shift>o"]),
            ("new-in-folder", self.new_folder_note, []),
            ("save", self.save_document, ["<primary>s"]),
            ("save-as", lambda: self.save_document(save_as=True), ["<primary><shift>s"]),
            ("preferences", self.show_preferences, ["<primary>comma"]),
            ("find", lambda: self.open_find(False), ["<primary>f"]),
            ("find-replace", lambda: self.open_find(True), ["<primary>h"]),
            ("find-next", lambda: self.navigate_find(1), ["F3", "<primary>g"]),
            ("find-previous", lambda: self.navigate_find(-1), ["<shift>F3", "<primary><shift>g"]),
            ("undo", lambda: self.undo_redo(False), ["<primary>z"]),
            ("redo", lambda: self.undo_redo(True), ["<primary><shift>z", "<primary>y"]),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, cb=callback: cb())
            self.add_action(action)
            app.set_accels_for_action(f"win.{name}", shortcuts)
        self.buffer.connect("changed", self.update_status)
        self.buffer.connect("modified-changed", self.update_status)
        self.buffer.connect("changed", self.schedule_preview)
        self.buffer.connect("notify::can-undo", self.update_undo_actions)
        self.buffer.connect("notify::can-redo", self.update_undo_actions)
        self.connect("destroy", self.cleanup_preview)
        self.connect("close-request", self.on_close_request)
        self.preference_handler = app.preferences.connect("notify::button-style", self.apply_button_style)
        self.gfm_preference_handler = app.preferences.connect("notify::gfm-enabled", self.apply_gfm_preference)
        self.connect("destroy", lambda _window: (
            app.preferences.disconnect(self.preference_handler),
            app.preferences.disconnect(self.gfm_preference_handler)))
        self.apply_button_style()
        self.update_status()
        self.update_undo_actions()
        self.refresh_preview()
        self.connect("unrealize", lambda _window: self.folder_browser.cleanup())
        if app.folder_state.folder:
            self.folder_browser.set_folder(app.folder_state.folder)

    def save_folder_state(self):
        try:
            self.get_application().folder_state.save(self.folder_browser.folder,
                                                     self.folder_browser.get_visible())
        except OSError as error:
            self.error("Could not remember folder settings", error)

    def toggle_sidebar(self, _action, _parameter):
        visible = not self.folder_browser.get_visible()
        self.folder_browser.set_visible(visible)
        self.sidebar_action.set_state(GLib.Variant("b", visible))
        self.save_folder_state()
        if visible and not self.folder_browser.folder:
            self.choose_folder()

    def choose_folder(self):
        if self.busy:
            return
        self.set_busy(True)
        dialog = Gtk.FileDialog(title="Choose notes folder")
        if self.folder_browser.folder:
            dialog.set_initial_folder(Gio.File.new_for_path(self.folder_browser.folder))

        def selected(chooser, result):
            self.set_busy(False)
            try:
                folder = chooser.select_folder_finish(result)
            except GLib.Error as error:
                self.dialog_error(error)
                return
            path = folder.get_path()
            if not path:
                self.error("Could not open folder", "Choose a local folder for your notes.")
                return
            self.folder_browser.set_folder(path)
            self.folder_browser.set_visible(True)
            self.sidebar_action.set_state(GLib.Variant("b", True))
            self.save_folder_state()

        dialog.select_folder(self, None, selected)

    def update_undo_actions(self, *_args):
        self.lookup_action("undo").set_enabled(not self.busy and self.buffer.get_can_undo())
        self.lookup_action("redo").set_enabled(not self.busy and self.buffer.get_can_redo())

    def new_folder_note(self):
        if self.busy:
            return
        folder = self.folder_browser.folder
        if not folder:
            self.error("Choose a notes folder", "Open a folder before creating a note in it.")
            return
        dialog = Adw.AlertDialog(heading="New Note", body=f"Create a Markdown note in:\n{folder}")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        entry = Gtk.Entry(placeholder_text="Note name.md", activates_default=True)
        entry.update_property([Gtk.AccessibleProperty.LABEL], ["New note filename"])
        hint = Gtk.Label(label="The .md extension is added if omitted.", wrap=True, xalign=0)
        hint.add_css_class("dim-label")
        box.append(entry)
        box.append(hint)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")
        dialog.set_response_enabled("create", False)

        def validate(_entry):
            try:
                note_filename(entry.get_text())
            except ValueError as error:
                dialog.set_response_enabled("create", False)
                hint.set_label(str(error) if entry.get_text() else "The .md extension is added if omitted.")
            else:
                dialog.set_response_enabled("create", True)
                hint.set_label("The .md extension is added if omitted.")

        def respond(_dialog, response):
            self.set_busy(False)
            if response == "create":
                try:
                    name = note_filename(entry.get_text())
                except ValueError as error:
                    self.error("Could not create note", error)
                    return
                target = Gio.File.new_for_path(str(Path(folder) / name))
                self.confirm_changes(lambda: self.create_folder_note(target))

        entry.connect("changed", validate)
        dialog.connect("response", respond)
        self.set_busy(True)
        dialog.present(self)
        entry.grab_focus()

    def create_folder_note(self, target):
        self.set_busy(True)

        def created(file, result):
            try:
                stream = file.create_finish(result)
            except GLib.Error as error:
                self.set_busy(False)
                self.error("Could not create note", error)
                return

            def closed(source, result):
                try:
                    source.close_finish(result)
                except GLib.Error as error:
                    self.set_busy(False)
                    self.error("Could not finish creating note", error)
                    return
                self.folder_browser.refresh()
                file.load_contents_async(None, self.loaded)

            stream.close_async(GLib.PRIORITY_DEFAULT, None, closed)

        # Exclusive creation fails if any file or symlink already has this
        # name. Never use replace_contents here: it would overwrite notes.
        target.create_async(Gio.FileCreateFlags.NONE, GLib.PRIORITY_DEFAULT, None, created)

    def undo_redo(self, redo=False):
        if self.busy:
            return
        focus = self.get_focus()
        # Search/replacement fields keep their own ordinary text undo. A
        # shortcut there must not unexpectedly edit the Markdown document.
        if isinstance(focus, Gtk.Editable):
            focus.activate_action("text.redo" if redo else "text.undo", None)
            return
        available = self.buffer.get_can_redo() if redo else self.buffer.get_can_undo()
        if not available:
            return
        if not self.editor_scroll.get_visible():
            self.set_view(True, self.preview_scroll.get_visible())
        if redo:
            self.buffer.redo()
        else:
            self.buffer.undo()
        self.focus_document()
        self.update_undo_actions()

    def toolbar_button(self, label, icon, action, *, toggle=False):
        button_type = Gtk.ToggleButton if toggle else Gtk.Button
        button = button_type(label=label, action_name=f"win.{action}")
        button.set_tooltip_text({"Editor": "Show or hide the editor",
                                 "Preview": "Show or hide the rendered preview"}.get(label, label))
        button.update_property([Gtk.AccessibleProperty.LABEL], [label])
        self.styled_buttons.append((button, label, icon))
        return button

    def open_find(self, replace=False):
        if self.busy:
            return
        if not self.editor_scroll.get_visible():
            self.set_view(True, self.preview_scroll.get_visible())
        self.find_bar.open(replace=replace)

    def navigate_find(self, direction):
        if self.busy:
            return
        if not self.find_bar.get_visible():
            self.open_find(False)
        self.find_bar.navigate(direction)

    def apply_button_style(self, *_args):
        icons = self.get_application().preferences.button_style == "icons"
        for button, label, icon in self.styled_buttons:
            if icons:
                button.set_icon_name(icon)
            else:
                button.set_label(label)
        if self.button_style_row:
            self.button_style_row.set_selected(1 if icons else 0)

    def show_preferences(self):
        if self.preferences_dialog:
            self.preferences_dialog.present(self)
            return
        dialog = Adw.PreferencesDialog(title="Preferences", search_enabled=False)
        page = Adw.PreferencesPage(title="Appearance", icon_name="preferences-desktop-appearance-symbolic")
        group = Adw.PreferencesGroup(title="Toolbar")
        row = Adw.ComboRow(title="Button style", subtitle="Choose text labels or compact icons",
                           model=Gtk.StringList.new(["Text", "Icons"]))
        row.set_selected(1 if self.get_application().preferences.button_style == "icons" else 0)

        def selected(_row, _property):
            style = "icons" if row.get_selected() == 1 else "text"
            try:
                self.get_application().preferences.set_button_style(style)
            except (OSError, ValueError) as error:
                row.set_selected(1 if self.get_application().preferences.button_style == "icons" else 0)
                self.error("Could not save preferences", error)

        row.connect("notify::selected", selected)
        group.add(row)
        page.add(group)
        dialog.add(page)
        markdown_page = Adw.PreferencesPage(title="Markdown", icon_name="text-x-generic-symbolic")
        markdown_group = Adw.PreferencesGroup(title="Formatting")
        gfm_row = Adw.SwitchRow(title="GitHub Flavoured Markdown (GFM)",
                               subtitle="Enable tables, task lists, strikethrough and automatic links",
                               active=self.get_application().preferences.gfm_enabled)

        def gfm_changed(_row, _property):
            self.set_gfm_preference(gfm_row.get_active())

        gfm_row.connect("notify::active", gfm_changed)
        markdown_group.add(gfm_row)
        markdown_page.add(markdown_group)
        dialog.add(markdown_page)
        self.gfm_row = gfm_row
        self.preferences_dialog, self.button_style_row = dialog, row

        def closed(_dialog):
            self.preferences_dialog = None
            self.button_style_row = None
            self.gfm_row = None

        dialog.connect("closed", closed)
        dialog.present(self)

    def toggle_pane(self, action, _parameter):
        editor = self.editor_action.get_state().get_boolean()
        preview = self.preview_action.get_state().get_boolean()
        if action == self.editor_action:
            editor = not editor
        else:
            preview = not preview
        self.set_view(editor, preview)

    def set_view(self, editor, preview):
        # Keep one pane visible, including when the last active button is hit.
        if not editor and not preview:
            return
        was_preview = self.preview_scroll.get_visible()
        if self.editor_scroll.get_visible() and was_preview:
            self.split_position = self.panes.get_position()
        self.editor_action.set_state(GLib.Variant("b", editor))
        self.preview_action.set_state(GLib.Variant("b", preview))
        self.editor_scroll.set_visible(editor)
        self.preview_scroll.set_visible(preview)
        if not editor:
            self.preview.grab_focus()
            self.find_bar.close(focus_editor=False)
        if editor and preview:
            self.panes.set_position(self.split_position)
        if preview and not was_preview:
            self.refresh_preview()
        elif not preview:
            self.cleanup_preview()
        self.focus_document()

    def cycle_view(self, _action, _parameter):
        current = (self.editor_scroll.get_visible(), self.preview_scroll.get_visible())
        modes = [(True, True), (True, False), (False, True)]
        self.set_view(*modes[(modes.index(current) + 1) % len(modes)])

    def focus_document(self):
        if self.editor_scroll.get_visible():
            self.editor.grab_focus()
        else:
            self.preview.grab_focus()

    def toggle_gfm(self, action, _parameter):
        self.set_gfm_preference(not action.get_state().get_boolean())

    def set_gfm_preference(self, enabled):
        try:
            self.get_application().preferences.set_gfm_enabled(enabled)
        except (OSError, ValueError) as error:
            if self.gfm_row:
                self.gfm_row.set_active(self.get_application().preferences.gfm_enabled)
            self.error("Could not save preferences", error)

    def apply_gfm_preference(self, *_args):
        enabled = self.get_application().preferences.gfm_enabled
        self.gfm_action.set_state(GLib.Variant("b", enabled))
        if self.gfm_row:
            self.gfm_row.set_active(enabled)
        self.update_status()
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
        self.preview.render(self.text(), gfm=self.gfm_action.get_state().get_boolean(),
                            document_uri=self.file.get_uri() if self.file else None)
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
        if self.buffer.get_modified():
            self.save_button.add_css_class("suggested-action")
        else:
            self.save_button.remove_css_class("suggested-action")
        name = self.file.get_basename() if self.file else "Untitled"
        self.title_widget.set_title(f"{'• ' if self.buffer.get_modified() else ''}{name}")
        self.set_title(f"{name} — My Notes")
        self.folder_browser.select(self.file.get_path() if self.file else None)
        text = self.text()
        mode = "GFM" if self.gfm_action.get_state().get_boolean() else "CommonMark"
        self.status.set_text(f"{mode}  ·  {len(text.split())} words  ·  {len(text)} characters")

    def set_busy(self, busy):
        focus = self.get_focus()
        if busy and focus and focus.is_ancestor(self.find_bar):
            self.focus_document()
        self.busy = busy
        self.open_button.set_sensitive(not busy)
        self.folder_browser.set_sensitive(not busy)
        self.editor.set_editable(not busy)
        for name in ("new", "open", "open-folder", "new-in-folder", "save", "save-as", "find", "find-replace", "find-next", "find-previous"):
            self.lookup_action(name).set_enabled(not busy)
        self.find_bar.set_sensitive(not busy)
        self.update_undo_actions()

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
        self.buffer.begin_irreversible_action()
        self.buffer.set_text("")
        self.buffer.end_irreversible_action()
        self.buffer.set_modified(False)
        self.update_status()
        self.focus_document()

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

    def open_recent(self, selected):
        def load():
            self.set_busy(True)
            selected.load_contents_async(None, self.loaded)
        self.confirm_changes(load)

    def remember_file(self, file):
        try:
            self.get_application().recent_notes.add(file)
        except OSError:
            # A history failure must never turn a successful save into a failure.
            self.toasts.add_toast(Adw.Toast(title="Could not save recent notes history"))

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
        self.remember_file(selected)
        self.buffer.begin_irreversible_action()
        self.buffer.set_text(text)
        self.buffer.end_irreversible_action()
        self.buffer.set_modified(False)
        self.set_busy(False)
        self.update_status()
        self.focus_document()

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
            self.remember_file(file)
            self.refresh_preview()
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
    def __init__(self, preferences_path=None, recent_path=None):
        super().__init__(application_id="net.anddav.MyNotes")
        self.preferences = ButtonPreferences(preferences_path)
        if recent_path is None and preferences_path is not None:
            recent_path = Path(preferences_path).parent / "recent-notes.json"
        self.recent_notes = RecentNotes(recent_path)
        state_path = (Path(preferences_path).parent / "folder-browser.json" if preferences_path else
                      Path(GLib.get_user_state_dir()) / "MyNotes/folder-browser.json")
        self.folder_state = FolderState(state_path)

    def do_startup(self):
        Adw.Application.do_startup(self)
        display = Gdk.Display.get_default()
        if display:
            theme = Gtk.IconTheme.get_for_display(display)
            theme.add_search_path(str(Path(__file__).resolve().parent / "data/icons"))
        Gtk.Window.set_default_icon_name("net.anddav.MyNotes")

    def do_activate(self):
        window = self.props.active_window or MyNotesWindow(self)
        window.present()
        window.focus_document()


if __name__ == "__main__":
    sys.exit(MyNotesApp().run(sys.argv))
