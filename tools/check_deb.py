"""Check an extracted .deb with system Python, without installing as root."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]

SMOKE = r'''
import importlib.util
import json
import pathlib
import sys
import time
root = pathlib.Path(sys.argv[1])
app_dir = root / 'usr/share/my-notes'
vendor = root / 'usr/lib/my-notes/vendor'
sys.path[:0] = [str(vendor), str(app_dir)]
sys.dont_write_bytecode = True
import markdown_it, cmarkgfm, _cffi_backend
for module in (markdown_it, cmarkgfm, _cffi_backend):
    assert pathlib.Path(module.__file__).is_relative_to(vendor), module.__file__
from markdown_engine import render_markdown, PARSER_VERSION, GFM_PARSER_VERSION
assert PARSER_VERSION == '4.0.0' and GFM_PARSER_VERSION == '2025.10.22'
fixture_dir = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('normalize', fixture_dir / 'normalize.py')
normalizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normalizer)
examples = json.loads((fixture_dir / 'spec-0.31.2.json').read_text())
failed = [e['example'] for e in examples if normalizer.normalize_html(render_markdown(e['markdown']))
          != normalizer.normalize_html(e['html'])]
assert not failed, failed
from main import MyNotesApp, MyNotesWindow, Gio, GLib, Gtk
app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
source = '- [x] Task\n\n~~Removed~~ https://example.org\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n'
w.buffer.set_text(source)
w.refresh_preview()
assert len(w.preview.task_widgets) == 1 and w.preview.task_widgets[0].get_active()
assert len(w.preview.table_widgets) == 1
assert any(href == 'https://example.org' for href, _title in w.preview.links.values())
w.show_preferences()
assert w.button_style_row is not None
w.preferences_dialog.close()
path = app_dir / 'examples/images-demo.md'
w.file = Gio.File.new_for_path(str(path))
w.buffer.set_text(path.read_text())
w.refresh_preview()
deadline = time.monotonic() + 5
while time.monotonic() < deadline and not any(i.state == 'loaded' for i in w.preview.image_widgets):
    GLib.MainContext.default().iteration(False)
    time.sleep(.01)
assert any(i.state == 'loaded' for i in w.preview.image_widgets)
w.destroy()
print('PASS: isolated system Python, private native modules, 652 CommonMark cases, GTK/GFM/tables/links/preferences/local image')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    for flag in ("--ctrl-tarfile", "--fsys-tarfile"):
        data = subprocess.check_output(["dpkg-deb", flag, str(package)])
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            assert all(item.uid == 0 and item.gid == 0 for item in archive), "Non-root package ownership"
    with tempfile.TemporaryDirectory(prefix="my-notes-package-test-") as directory:
        root = Path(directory)
        subprocess.run(["dpkg-deb", "--extract", str(package), str(root)], check=True)
        control = root / "control"
        subprocess.run(["dpkg-deb", "--control", str(package), str(control)], check=True)
        for line in (control / "md5sums").read_text().splitlines():
            digest, name = line.split("  ", 1)
            assert hashlib.md5((root / name).read_bytes()).hexdigest() == digest, name
        desktop = root / "usr/share/applications/net.anddav.MyNotes.desktop"
        assert "Exec=/usr/bin/my-notes\n" in desktop.read_text()
        assert "/home/" not in desktop.read_text()
        wrapper = root / "usr/bin/my-notes"
        assert wrapper.stat().st_mode & 0o111
        assert "/home/" not in wrapper.read_text()
        assert not list(root.rglob("__pycache__"))
        assert not list(root.rglob(".git"))
        assert not list(root.rglob(".venv"))
        env = dict(os.environ, XDG_CONFIG_HOME=str(root / "test-config"), PYTHONPATH="/nonexistent-test-path")
        subprocess.run(["/usr/bin/python3", "-I", "-c", SMOKE, str(root), str(ROOT / "tests/commonmark")],
                       check=True, env=env, timeout=30)
        help_run = subprocess.run(["/usr/bin/python3", "-I", str(root / "usr/share/my-notes/launch.py"), "--help"],
                                  check=True, env=env, capture_output=True, text=True, timeout=10)
        assert "Usage:" in help_run.stdout
    print("PASS: package ownership, file checksums, launcher paths, packaged entry point, no development environment required")


if __name__ == "__main__":
    main()
