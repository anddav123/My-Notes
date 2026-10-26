"""Bounded background image loading for native Markdown previews."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import Request, urlopen

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

MAX_BYTES = 10 * 1024 * 1024
_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="note-image")


def resolve_image(source, document_uri=None):
    source = source.strip()
    if not source:
        raise ValueError("No image destination.")
    if source.startswith("//"):
        source = "https:" + source
    parsed = urlsplit(source)
    if not parsed.scheme:
        if source.startswith("/"):
            source = Path(unquote(parsed.path)).as_uri()
        elif document_uri:
            source = urljoin(document_uri, source)
        else:
            raise ValueError("Save this note to load images relative to its folder.")
        parsed = urlsplit(source)
    if parsed.scheme not in ("file", "http", "https"):
        raise ValueError("Only local files and HTTP/HTTPS images are supported.")
    if parsed.scheme == "file" and parsed.netloc not in ("", "localhost"):
        raise ValueError("Remote file shares are not supported.")
    return source


def load_image(uri, max_width, max_height):
    parsed = urlsplit(uri)
    stamp = None
    if parsed.scheme == "file":
        stat = Path(unquote(parsed.path)).stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    return _decode_image(uri, stamp, max_width, max_height)


@lru_cache(maxsize=32)
def _decode_image(uri, _stamp, max_width, max_height):
    if urlsplit(uri).scheme == "file":
        stream = Path(unquote(urlsplit(uri).path)).open("rb")
    else:
        stream = urlopen(Request(uri, headers={"User-Agent": "My-Notes/1.0"}), timeout=10)
    with stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Image exceeds the 10 MB preview limit.")
    loader = GdkPixbuf.PixbufLoader()

    def prepared(source, width, height):
        ratio = min(1.0, max_width / max(1, width), max_height / max(1, height))
        source.set_size(max(1, round(width * ratio)), max(1, round(height * ratio)))

    loader.connect("size-prepared", prepared)
    try:
        loader.write(data)
        loader.close()
    except Exception:
        try:
            loader.close()
        except GLib.Error:
            pass
        raise
    pixbuf = loader.get_pixbuf()
    if pixbuf is None:
        raise ValueError("This file could not be decoded as an image.")
    return pixbuf


class PreviewImage(Gtk.Box):
    def __init__(self, source, alt, title, document_uri, remote_allowed,
                 max_width=480, max_height=320):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                         halign=Gtk.Align.START)
        self.active = True
        self.future = None
        self.state = "pending"
        self.picture = Gtk.Picture(can_shrink=True, content_fit=Gtk.ContentFit.CONTAIN,
                                   alternative_text=alt or "Image")
        self.picture.set_visible(False)
        self.append(self.picture)
        self.message = Gtk.Label(label=alt or "Image", wrap=True, xalign=0,
                                 max_width_chars=40)
        self.message.add_css_class("dim-label")
        self.append(self.message)
        self.set_tooltip_text("\n".join(filter(None, (title, source))))
        self.max_width, self.max_height = max_width, max_height
        self.remote_allowed = remote_allowed
        try:
            self.uri = resolve_image(source, document_uri)
        except ValueError as error:
            self.fail(error)
            return
        self.load_button = None
        if urlsplit(self.uri).scheme in ("http", "https") and self.uri not in remote_allowed:
            self.state = "remote"
            self.load_button = Gtk.Button(label="Load image", halign=Gtk.Align.START)
            self.load_button.connect("clicked", self.allow_remote)
            self.append(self.load_button)
        else:
            self.start_load()

    def allow_remote(self, _button):
        self.remote_allowed.add(self.uri)
        self.start_load()

    def start_load(self):
        if self.load_button:
            self.load_button.set_visible(False)
        self.state = "loading"
        self.message.set_label(self.picture.get_alternative_text() + " — Loading…")
        self.future = _workers.submit(load_image, self.uri, self.max_width, self.max_height)
        self.future.add_done_callback(lambda future: GLib.idle_add(self.loaded, future))

    def loaded(self, future):
        if not self.active:
            return GLib.SOURCE_REMOVE
        try:
            pixbuf = future.result()
            self.picture.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            self.picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
            # TextView anchors track the direct child's request, not every
            # descendant's change from placeholder text to a loaded picture.
            self.set_size_request(pixbuf.get_width(), pixbuf.get_height())
            self.picture.set_visible(True)
            self.message.set_visible(False)
            self.state = "loaded"
        except Exception as error:
            self.fail(error)
        return GLib.SOURCE_REMOVE

    def fail(self, error):
        self.state = "error"
        self.message.set_label(self.picture.get_alternative_text() + " — Image unavailable")
        self.set_tooltip_text(str(error))

    def detach(self):
        self.active = False
        if self.future:
            self.future.cancel()
