import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw


class MyNotesWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        self.set_title("My Notes")
        self.set_default_size(900, 600)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        toolbar.add_top_bar(header)

        label = Gtk.Label(
            label="Welcome to My Notes!"
        )

        toolbar.set_content(label)
        self.set_content(toolbar)


class MyNotesApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="net.anddav.MyNotes"
        )

    def do_activate(self):
        window = self.props.active_window

        if window is None:
            window = MyNotesWindow(self)

        window.present()


app = MyNotesApp()
app.run()
