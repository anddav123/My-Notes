"""Image integration checks. HTTP requests stay on a temporary loopback server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time

from main import MyNotesApp, MyNotesWindow, Gio, GLib
from images import resolve_image, MAX_BYTES
from gi.repository import GdkPixbuf


def wait(predicate):
    deadline = time.monotonic() + 8
    while not predicate():
        assert time.monotonic() < deadline, "Image loading timed out"
        GLib.MainContext.default().iteration(False)
        time.sleep(.01)


app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
w.present()
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    image_path = folder / "wide image.png"
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 1200, 600)
    pixbuf.fill(0x4778D4FF)
    pixbuf.savev(str(image_path), "png", [], [])
    png = image_path.read_bytes()
    note = folder / "note.md"
    w.file = Gio.File.new_for_path(str(note))
    source = '![Alt description](wide%20image.png "Image title")\n'
    w.buffer.set_text(source)
    w.refresh_preview()
    image = w.preview.image_widgets[0]
    wait(lambda: image.state == "loaded")
    texture = image.picture.get_paintable()
    assert 0 < texture.get_width() <= 480 and 0 < texture.get_height() <= 320
    assert texture.get_width() == texture.get_height() * 2
    wait(lambda: image.picture.get_width() > 0)
    assert image.picture.get_width() >= texture.get_width()
    assert image.picture.get_height() >= texture.get_height()
    assert image.picture.get_alternative_text() == "Alt description"
    assert "Image title" in image.get_tooltip_text()
    assert w.text() == source and w.buffer.get_modified()

    # File URLs, reference images, linked images, and table images.
    w.preview.render(f'![Absolute]({image_path.as_uri()})')
    wait(lambda: w.preview.image_widgets[0].state == "loaded")
    w.preview.render('![Ref][pic]\n\n[pic]: wide%20image.png "Ref title"', document_uri=note.as_uri())
    wait(lambda: w.preview.image_widgets[0].state == "loaded")
    assert w.preview.image_widgets[0].picture.get_alternative_text() == "Ref"
    opened = []
    w.launch_link = lambda kind, uri: opened.append((kind, uri))
    w.preview.render('[![Linked](wide%20image.png)](https://example.org)', document_uri=note.as_uri())
    wait(lambda: w.preview.image_widgets[0].state == "loaded")
    w.preview.image_widgets[0].link_button.emit("clicked")
    assert opened == [("uri", "https://example.org")]
    w.preview.render('| Image |\n| --- |\n| ![Table](wide%20image.png) |', document_uri=note.as_uri())
    wait(lambda: w.preview.image_widgets[0].state == "loaded")
    assert w.preview.image_widgets[0].picture.get_paintable().get_width() <= 160

    # Unsaved-relative, nonexistent, corrupt, and oversized files show fallbacks.
    w.preview.render(source)
    assert w.preview.image_widgets[0].state == "error"
    corrupt = folder / "corrupt.png"
    corrupt.write_text("not an image")
    oversized = folder / "oversized.png"
    with oversized.open("wb") as stream:
        stream.truncate(MAX_BYTES + 1)
    for name in ("missing.png", "corrupt.png", "oversized.png"):
        w.preview.render(f'![Fallback]({name})', document_uri=note.as_uri())
        wait(lambda: w.preview.image_widgets[0].state == "error")
        assert "Fallback" in w.preview.image_widgets[0].message.get_label()

    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            if self.path == "/slow.png":
                time.sleep(.25)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        remote = f'![Remote]({origin}/image.png)'
        w.preview.render(remote)
        image = w.preview.image_widgets[0]
        assert image.state == "remote" and not hits
        image.load_button.emit("clicked")
        wait(lambda: image.state == "loaded")
        assert hits == ["/image.png"]
        w.preview.render(remote)
        wait(lambda: w.preview.image_widgets[0].state == "loaded")
        assert hits == ["/image.png"], "Rerender downloaded an already cached image"
        w.preview.render(f'![Slow]({origin}/slow.png)')
        old_image = w.preview.image_widgets[0]
        old_image.load_button.emit("clicked")
        w.preview.render("Replacement note")
        assert not old_image.active and not w.preview.image_widgets
        wait(lambda: old_image.future.done())
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        assert not w.preview.image_widgets
    finally:
        server.shutdown()
        server.server_close()

    # Unsupported sources never become a network request.
    for uri in ("data:image/png,abc", "javascript:alert(1)", "file://server/share/a.png"):
        try:
            resolve_image(uri)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsupported source accepted: {uri}")
w.destroy()
print("PASS: local/reference/file/table/linked images, scaling and alt text, fallbacks, remote opt-in/cache, stale-load cleanup")
