"""Literal find/replace in the Markdown editor, with non-overlapping matches."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, GObject


class FindReplaceBar(Gtk.Box):
    __gsignals__ = {"replaced": (GObject.SignalFlags.RUN_LAST, None, (int,))}

    def __init__(self, editor):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.editor = editor
        self.buffer = editor.get_buffer()
        self.matches = []
        self.current = -1
        self.pending = None
        self.replacing = False
        self.match_tag = self.buffer.create_tag("find-match")
        self.current_tag = self.buffer.create_tag("find-current")
        self.set_visible(False)
        row = Gtk.Box(spacing=6)
        self.find_entry = Gtk.SearchEntry(placeholder_text="Find in note", hexpand=True)
        self.find_entry.update_property([Gtk.AccessibleProperty.LABEL], ["Find in Markdown source"])
        row.append(self.find_entry)
        self.count_label = Gtk.Label()
        self.count_label.add_css_class("dim-label")
        row.append(self.count_label)
        self.previous_button = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Previous match (Shift+F3)")
        self.next_button = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Next match (F3)")
        row.append(self.previous_button)
        row.append(self.next_button)
        self.match_case = Gtk.CheckButton(label="Match case")
        row.append(self.match_case)
        close = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close search (Esc)")
        close.add_css_class("flat")
        row.append(close)
        self.append(row)
        self.replace_row = Gtk.Box(spacing=6)
        self.replace_entry = Gtk.Entry(placeholder_text="Replace with", hexpand=True)
        self.replace_entry.update_property([Gtk.AccessibleProperty.LABEL], ["Replacement text"])
        self.replace_row.append(self.replace_entry)
        self.replace_button = Gtk.Button(label="Replace")
        self.replace_all_button = Gtk.Button(label="Replace All")
        self.replace_row.append(self.replace_button)
        self.replace_row.append(self.replace_all_button)
        self.append(self.replace_row)
        self.find_entry.connect("search-changed", lambda _entry: self.refresh(select=True))
        self.find_entry.connect("next-match", lambda _entry: self.navigate(1))
        self.find_entry.connect("previous-match", lambda _entry: self.navigate(-1))
        self.find_entry.connect("stop-search", lambda _entry: self.close())
        self.match_case.connect("toggled", lambda _button: self.refresh(select=True))
        self.previous_button.connect("clicked", lambda _button: self.navigate(-1))
        self.next_button.connect("clicked", lambda _button: self.navigate(1))
        self.replace_button.connect("clicked", lambda _button: self.replace_current())
        self.replace_all_button.connect("clicked", lambda _button: self.replace_all())
        close.connect("clicked", lambda _button: self.close())
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.key_pressed)
        self.add_controller(keys)
        self.buffer_handler = self.buffer.connect("changed", self.document_changed)
        self.connect("destroy", self.cleanup)
        self.update_controls()

    def open(self, *, replace=False):
        selection = self.buffer.get_selection_bounds()
        if len(selection) == 2:
            selected = self.buffer.get_text(*selection, True)
            if selected and "\n" not in selected and len(selected) <= 1024:
                self.find_entry.set_text(selected)
        self.replace_row.set_visible(replace)
        self.set_visible(True)
        self.refresh(select=True)
        self.find_entry.grab_focus()
        self.find_entry.select_region(0, -1)

    def cancel_pending(self):
        if self.pending is not None:
            GLib.source_remove(self.pending)
            self.pending = None

    def close(self, *, focus_editor=True):
        self.cancel_pending()
        if focus_editor and self.editor.get_mapped():
            self.editor.grab_focus()
        self.set_visible(False)
        self.buffer.remove_tag(self.match_tag, *self.buffer.get_bounds())
        self.buffer.remove_tag(self.current_tag, *self.buffer.get_bounds())
        self.matches = []
        self.current = -1
        self.update_controls()

    def cleanup(self, *_args):
        self.cancel_pending()
        self.buffer.disconnect(self.buffer_handler)

    def document_changed(self, *_args):
        if self.replacing or not self.get_visible():
            return
        self.cancel_pending()
        self.pending = GLib.timeout_add(100, self.scan_later)

    def scan_later(self):
        self.pending = None
        self.refresh()
        return GLib.SOURCE_REMOVE

    def selection_offsets(self):
        selected = self.buffer.get_selection_bounds()
        return tuple(item.get_offset() for item in selected) if len(selected) == 2 else None

    def refresh(self, *, select=False):
        self.cancel_pending()
        if not self.get_visible():
            return
        old = self.matches[self.current] if 0 <= self.current < len(self.matches) else None
        self.buffer.remove_tag(self.match_tag, *self.buffer.get_bounds())
        self.buffer.remove_tag(self.current_tag, *self.buffer.get_bounds())
        self.matches = []
        self.current = -1
        query = self.find_entry.get_text()
        if query:
            flags = Gtk.TextSearchFlags.TEXT_ONLY
            if not self.match_case.get_active():
                flags |= Gtk.TextSearchFlags.CASE_INSENSITIVE
            cursor = self.buffer.get_start_iter()
            while True:
                found = cursor.forward_search(query, flags, None)
                if not found:
                    break
                start, end = found
                self.matches.append((start.get_offset(), end.get_offset()))
                if start.equal(end):
                    break
                cursor = end.copy()
        found_color, color = self.editor.get_style_context().lookup_color("accent_bg_color")
        if not found_color:
            color = Gdk.RGBA()
            color.parse("#3584e4")
        color.alpha = .22
        self.match_tag.set_property("background-rgba", color)
        color.alpha = .45
        self.current_tag.set_property("background-rgba", color)
        for start, end in self.matches:
            self.buffer.apply_tag(self.match_tag, self.buffer.get_iter_at_offset(start),
                                  self.buffer.get_iter_at_offset(end))
        if self.matches:
            selected = self.selection_offsets()
            caret = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_offset()
            if selected in self.matches:
                self.current = self.matches.index(selected)
            elif not select and old in self.matches:
                self.current = self.matches.index(old)
            else:
                self.current = next((i for i, (start, _end) in enumerate(self.matches) if start >= caret), 0)
            self.highlight_current(select=select)
        self.update_controls()

    def highlight_current(self, *, select=False):
        self.buffer.remove_tag(self.current_tag, *self.buffer.get_bounds())
        if 0 <= self.current < len(self.matches):
            start, end = self.matches[self.current]
            first, last = self.buffer.get_iter_at_offset(start), self.buffer.get_iter_at_offset(end)
            self.buffer.apply_tag(self.current_tag, first, last)
            if select:
                self.buffer.select_range(first, last)
                self.editor.scroll_to_iter(first, .15, False, 0, 0)

    def update_controls(self):
        count = len(self.matches)
        self.count_label.set_text(f"{self.current + 1} of {count}" if count and self.current >= 0
                                 else "0 matches" if self.find_entry.get_text() else "")
        for button in (self.previous_button, self.next_button, self.replace_button, self.replace_all_button):
            button.set_sensitive(count > 0)
        if self.find_entry.get_text() and not count:
            self.find_entry.add_css_class("error")
        else:
            self.find_entry.remove_css_class("error")

    def navigate(self, direction):
        self.refresh()
        if not self.matches:
            return
        selected = self.selection_offsets()
        if selected in self.matches:
            self.current = (self.matches.index(selected) + direction) % len(self.matches)
        else:
            caret = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_offset()
            if direction > 0:
                self.current = next((i for i, (start, _end) in enumerate(self.matches) if start >= caret), 0)
            else:
                self.current = next((i for i in range(len(self.matches)-1, -1, -1)
                                     if self.matches[i][0] < caret), len(self.matches)-1)
        self.highlight_current(select=True)
        self.update_controls()

    def replace_current(self):
        if not self.editor.get_editable() or not self.get_visible():
            return 0
        self.refresh()
        selected = self.selection_offsets()
        if selected not in self.matches:
            self.navigate(1)
            return 0
        start, end = selected
        replacement = self.replace_entry.get_text()
        self.replacing = True
        self.buffer.begin_user_action()
        try:
            first, last = self.buffer.get_iter_at_offset(start), self.buffer.get_iter_at_offset(end)
            self.buffer.delete(first, last)
            self.buffer.insert(first, replacement)
        finally:
            self.buffer.end_user_action()
            self.replacing = False
        self.buffer.place_cursor(self.buffer.get_iter_at_offset(start + len(replacement)))
        self.refresh()
        self.navigate(1)
        self.emit("replaced", 1)
        return 1

    def replace_all(self):
        if not self.editor.get_editable() or not self.get_visible():
            return 0
        self.refresh()
        matches = list(self.matches)
        if not matches:
            return 0
        replacement = self.replace_entry.get_text()
        self.replacing = True
        self.buffer.begin_user_action()
        try:
            for start, end in reversed(matches):
                first, last = self.buffer.get_iter_at_offset(start), self.buffer.get_iter_at_offset(end)
                self.buffer.delete(first, last)
                self.buffer.insert(first, replacement)
        finally:
            self.buffer.end_user_action()
            self.replacing = False
        self.refresh()
        self.emit("replaced", len(matches))
        return len(matches)

    def key_pressed(self, _controller, keyval, _keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            root = self.get_root()
            focus = root.get_focus() if root else None
            if focus and (focus == self.replace_entry or focus.is_ancestor(self.replace_entry)):
                self.replace_current()
            else:
                self.navigate(-1 if state & Gdk.ModifierType.SHIFT_MASK else 1)
            return True
        return False
