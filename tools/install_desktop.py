"""Install the development checkout's icon and launcher for the current user."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

APP_ID = "net.anddav.MyNotes"
ROOT = Path(__file__).resolve().parents[1]


def quote_exec_argument(value):
    if any(char in value for char in ("\n", "\r", "\0")):
        raise ValueError("The project path cannot contain newline or NUL characters.")
    # Exec has quoting rules plus desktop-file string escaping; it is not a shell.
    quoted = ''.join('\\' + c if c in ('"', '`', '$', '\\') else c for c in value)
    return '"' + quoted.replace('\\', '\\\\').replace('%', '%%') + '"'


def install(data_home=None, root=ROOT, refresh=True):
    root = Path(root).resolve()
    data_home = Path(data_home or os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share").expanduser()
    if not data_home.is_absolute():
        raise ValueError("The application data directory must be absolute.")
    for required in (root / "run.sh", root / ".venv/bin/python", root / "main.py"):
        if not required.is_file():
            raise FileNotFoundError(f"Set up the project environment first: missing {required}")
    source_icon = root / f"data/icons/hicolor/scalable/apps/{APP_ID}.svg"
    template = (root / f"data/{APP_ID}.desktop.in").read_text(encoding="utf-8")
    if not source_icon.is_file():
        raise FileNotFoundError(source_icon)
    applications = data_home / "applications"
    launcher = applications / f"{APP_ID}.desktop"
    if launcher.exists() and "X-MyNotes-Managed=true" not in launcher.read_text(encoding="utf-8"):
        raise FileExistsError(f"An independently configured launcher already exists: {launcher}")
    icon_dir = data_home / "icons/hicolor/scalable/apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    applications.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_icon, icon_dir / source_icon.name)
    launcher.write_text(template.replace("@RUN_SCRIPT@", quote_exec_argument(str(root / "run.sh"))),
                        encoding="utf-8")
    validator = shutil.which("desktop-file-validate")
    if validator:
        subprocess.run([validator, str(launcher)], check=True)
    if refresh:
        updater = shutil.which("update-desktop-database")
        if updater:
            subprocess.run([updater, str(applications)], check=True)
        cache = shutil.which("gtk-update-icon-cache")
        if cache:
            subprocess.run([cache, "--force", "--ignore-theme-index", str(data_home / "icons/hicolor")], check=True)
    return launcher


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-home", type=Path, help="Override the per-user application data directory")
    args = parser.parse_args()
    print(f"Installed My Notes: {install(args.data_home)}")
