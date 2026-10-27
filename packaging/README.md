# My Notes Debian package

The initial package is **my-notes_0.1.0-1_amd64.deb**, targeting **Debian 13
amd64 with Python 3.13**. It is not an architecture-independent package and is
not intended for Debian 12 or a different Python minor version.

## Install on a machine

From the project folder:

~~~sh
sudo apt install ./dist/my-notes_0.1.0-1_amd64.deb
~~~

APT installs any missing Debian GTK/Python dependencies. Pinned Markdown and
CFFI dependencies are bundled privately; installation does not run pip, need
the development checkout, or alter Debian's Python packages.

The installed locations are:

- /usr/bin/my-notes: application command.
- /usr/share/my-notes/: application code, icon resources and example notes.
- /usr/lib/my-notes/vendor/: pinned, private Python dependencies.
- /usr/share/applications/net.anddav.MyNotes.desktop: system app-grid entry.
- /usr/share/icons/hicolor/scalable/apps/net.anddav.MyNotes.svg: system icon.
- /usr/share/doc/my-notes/: application licence, README and dependency build information.

Notes and preferences remain per user. Removal does not delete them:

~~~sh
sudo apt remove my-notes
~~~

Install a later version with sudo apt install ./dist/<new-package>.deb.

## Switch from the development launcher

Per-user application entries take precedence over system entries with the
same ID. After installing, back up the development entry and its icon so GNOME
uses the system package. These commands retain the old files:

~~~sh
mkdir -p ~/.local/share/my-notes-launcher-backup
mv -n ~/.local/share/applications/net.anddav.MyNotes.desktop ~/.local/share/my-notes-launcher-backup/
mv -n ~/.local/share/icons/hicolor/scalable/apps/net.anddav.MyNotes.svg ~/.local/share/my-notes-launcher-backup/
~~~

Run only the moves whose source files exist. Close the old running app first,
then run my-notes or select My Notes in GNOME. The package deliberately does
not edit users' home directories or replace their launchers automatically.
The development checkout and sh run.sh remain available separately.

## Build again

On Debian 13 amd64, from this checkout:

~~~sh
python3 tools/build_deb.py --version 0.1.0-1
WAYLAND_DISPLAY=wayland-0 python3 tools/check_deb.py dist/my-notes_0.1.0-1_amd64.deb
~~~

The builder verifies downloaded archives against the exact SHA-256 values in
packaging/deb-dependencies.json. It downloads only missing cache entries.
Cached builds can run offline. Use --refresh-lock deliberately after changing
the pinned requirements.txt versions. The build requires standard Python,
dpkg-deb, and network access only for uncached dependency artifacts.

Outputs:

- The binary .deb.
- A companion my-notes_<version>-sources.tar.gz containing application/build
  source and the exact upstream dependency source archives.
- A SHA-256 file covering both artifacts.

The binary contains root-owned files and no virtual environment, user
preferences, private keys, Git metadata, home-folder launcher references, or
development-path dependency. Python runs in isolated mode and uses the private
dependencies before Debian's versions.

## Verification and limits

The extracted-package test runs system /usr/bin/python3, not .venv, and
checks native imports, all 652 CommonMark examples, GTK startup, GFM task/table
rendering, links, Preferences and a local image. It verifies installed-file
checksums, root ownership, launcher paths and the packaged entry point.

APT installation was simulated successfully. The package has not yet been
installed or removed as root on a separate clean machine, and lintian was not
available on the build VM. Existing GFM and GTK limitations documented in
docs/ are unchanged by packaging. This is a package of the current app,
not a claim that those outstanding issues have been fixed.
