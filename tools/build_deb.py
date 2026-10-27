"""Build a self-contained My Notes .deb for Debian 13 / Python 3.13 / amd64.

GTK and Python come from Debian. Pinned application dependencies are bundled
privately; package installation never runs pip or changes system Python.
"""
import argparse
from email.parser import Parser
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "packaging/deb-dependencies.json"
MODULES = ("main.py", "preview.py", "markdown_engine.py", "links.py", "images.py", "preferences.py",
           "find_replace.py", "recent_notes.py")


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refresh_lock():
    dependencies = []
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        with urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as response:
            metadata = json.load(response)
        wheels = [item for item in metadata["urls"] if item["filename"].endswith(".whl")
                  and ("py3-none-any" in item["filename"] or
                       ("cp313-cp313-" in item["filename"] and "manylinux" in item["filename"]
                        and "x86_64" in item["filename"]))]
        sources = [item for item in metadata["urls"] if item["packagetype"] == "sdist"]
        if len(wheels) != 1 or len(sources) != 1:
            raise ValueError(f"Expected one compatible wheel and one source archive for {name}")
        def entry(item):
            return {"filename": item["filename"], "url": item["url"], "sha256": item["digests"]["sha256"]}
        dependencies.append({"name": name, "version": version, "wheel": entry(wheels[0]), "source": entry(sources[0])})
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"target": "Debian 13 amd64 / CPython 3.13", "dependencies": dependencies}, indent=2) + "\n")


def fetch(entry, cache):
    path = cache / entry["filename"]
    if not path.exists():
        with urlopen(entry["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Download hash mismatch: {path.name}")
        path.write_bytes(data)
    if sha256(path) != entry["sha256"]:
        raise ValueError(f"Cached hash mismatch: {path.name}")
    return path


def build(args):
    if sys.version_info[:2] != (3, 13) or run("dpkg", "--print-architecture") != "amd64":
        raise RuntimeError("Build this target using Debian 13 amd64 with Python 3.13")
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+:~\-]*", args.version):
        raise ValueError("Invalid Debian package version")
    if args.refresh_lock:
        refresh_lock()
    lock = json.loads(LOCK.read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "deb-downloads"
    cache.mkdir(exist_ok=True)
    dependencies = lock["dependencies"]
    wheels = [fetch(item["wheel"], cache) for item in dependencies]
    sources = [fetch(item["source"], cache) for item in dependencies]
    commit = run("git", "-C", str(ROOT), "rev-parse", "HEAD")
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH") or run("git", "-C", str(ROOT), "log", "-1", "--format=%ct"))
    maintainer = args.maintainer or run("git", "-C", str(ROOT), "log", "-1", "--format=%an <%ae>")
    if "\n" in maintainer or not re.fullmatch(r"[^<>]+ <[^<>\s]+@[^<>\s]+>", maintainer):
        raise ValueError("Supply a valid Maintainer name and email")
    stem = f"my-notes_{args.version}_amd64"
    package = output / f"{stem}.deb"
    with tempfile.TemporaryDirectory(prefix="my-notes-deb-") as directory:
        stage = Path(directory)
        app = stage / "usr/share/my-notes"
        vendor = stage / "usr/lib/my-notes/vendor"
        doc = stage / "usr/share/doc/my-notes"
        for path in (app, vendor, doc, stage / "usr/bin", stage / "DEBIAN"):
            path.mkdir(parents=True, exist_ok=True)
        for name in MODULES:
            shutil.copyfile(ROOT / name, app / name)
        for name in ("data", "examples"):
            shutil.copytree(ROOT / name, app / name)
        shutil.copyfile(ROOT / "packaging/launch.py", app / "launch.py")
        for wheel in wheels:
            with zipfile.ZipFile(wheel) as archive:
                for item in archive.infolist():
                    target = (vendor / item.filename).resolve()
                    if not target.is_relative_to(vendor.resolve()) or ".data/" in item.filename:
                        raise ValueError(f"Unexpected wheel path: {item.filename}")
                archive.extractall(vendor)
        icons = stage / "usr/share/icons/hicolor/scalable/apps"
        icons.mkdir(parents=True)
        shutil.copyfile(ROOT / "data/icons/hicolor/scalable/apps/net.anddav.MyNotes.svg", icons / "net.anddav.MyNotes.svg")
        applications = stage / "usr/share/applications"
        applications.mkdir(parents=True)
        desktop = (ROOT / "data/net.anddav.MyNotes.desktop.in").read_text()
        desktop = desktop.replace("Exec=/usr/bin/sh @RUN_SCRIPT@", "Exec=/usr/bin/my-notes")
        desktop = desktop.replace("TryExec=/usr/bin/sh", "TryExec=/usr/bin/my-notes")
        desktop = desktop.replace("X-MyNotes-Managed=true\n", "")
        desktop_file = applications / "net.anddav.MyNotes.desktop"
        desktop_file.write_text(desktop)
        if shutil.which("desktop-file-validate"):
            subprocess.run(["desktop-file-validate", str(desktop_file)], check=True)
        launcher = stage / "usr/bin/my-notes"
        launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 -I /usr/share/my-notes/launch.py "$@"\n')
        for name in ("LICENSE", "README.md"):
            shutil.copyfile(ROOT / name, doc / name)
        shutil.copyfile(ROOT / "packaging/README.md", doc / "README.Debian")
        # Retain notices for native code included in upstream dependency sources,
        # in addition to the wheel licence metadata already installed privately.
        for source in sources:
            with tarfile.open(source, "r:*") as archive:
                for member in archive.getmembers():
                    path = Path(member.name)
                    if (member.isfile() and member.size < 1024 * 1024
                            and not path.is_absolute() and ".." not in path.parts
                            and re.fullmatch(r"(LICENSE|COPYING|COPYRIGHT|NOTICE)([.-].*)?",
                                             path.name, flags=re.IGNORECASE)):
                        notice = doc / "upstream-licenses" / source.stem / path
                        notice.parent.mkdir(parents=True, exist_ok=True)
                        notice.write_bytes(archive.extractfile(member).read())
        (doc / "copyright").write_text(
            "My Notes: Andrew Davies and contributors, GPL-3.0.\n"
            "See LICENSE for the application licence.\n"
            "Bundled dependency licences accompany their dist-info directories in\n"
            "/usr/lib/my-notes/vendor/. Exact upstream source archives accompany\n"
            "the build's -sources.tar.gz artifact.\n")
        metadata = {"package": "my-notes", "version": args.version, "architecture": "amd64",
                    "target": "Debian 13 / Python 3.13", "source_commit": commit,
                    "dependencies": dependencies}
        (doc / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n")
        size = sum((p.stat().st_size + 1023) // 1024 for p in stage.rglob("*") if p.is_file())
        (stage / "DEBIAN/control").write_text(
            f"Package: my-notes\nVersion: {args.version}\nArchitecture: amd64\n"
            f"Maintainer: {maintainer}\nSection: editors\nPriority: optional\nInstalled-Size: {size}\n"
            "Depends: python3 (>= 3.13~), python3 (<< 3.14), python3-gi, "
            "gir1.2-gtk-4.0 (>= 4.10), gir1.2-adw-1 (>= 1.5), "
            "gir1.2-gdkpixbuf-2.0, librsvg2-common, adwaita-icon-theme, libc6 (>= 2.41), "
            "hicolor-icon-theme, desktop-file-utils\n"
            "Homepage: https://github.com/anddav123/My-Notes\n"
            "Description: GTK Markdown notes editor with live preview\n"
            " Write and preview CommonMark and GitHub Flavored Markdown notes.\n"
            " Includes native tables, links, images, viewing modes and preferences.\n")
        hashes = []
        for path in stage.rglob("*"):
            if path.is_file() and not path.is_relative_to(stage / "DEBIAN"):
                hashes.append(f"{hashlib.md5(path.read_bytes()).hexdigest()}  {path.relative_to(stage)}")
        (stage / "DEBIAN/md5sums").write_text("\n".join(sorted(hashes)) + "\n")
        for path in [stage, *stage.rglob("*")]:
            path.chmod(0o755 if path.is_dir() or path == launcher else 0o644)
            os.utime(path, (epoch, epoch))
        env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(package)], check=True, env=env)
    # Source companion: app source/build scripts plus the exact upstream sdists.
    source_archive = output / f"my-notes_{args.version}-sources.tar.gz"
    names = run("git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard").splitlines()
    with source_archive.open("wb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", mtime=epoch) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name in sorted(set(names)):
                path = ROOT / name
                if path.is_file() and not path.is_symlink():
                    archive.add(path, arcname=f"my-notes/{name}", recursive=False)
            for source in sources:
                archive.add(source, arcname=f"upstream-sources/{source.name}")
    checksums = output / f"{stem}.sha256"
    checksums.write_text(f"{sha256(package)}  {package.name}\n{sha256(source_archive)}  {source_archive.name}\n")
    print(f"Package: {package}\nSources: {source_archive}\nChecksums: {checksums}")
    return package


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0-1")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--maintainer")
    parser.add_argument("--refresh-lock", action="store_true", help="Refresh exact dependency URLs/hashes from PyPI")
    build(parser.parse_args())
