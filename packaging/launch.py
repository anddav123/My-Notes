"""Launch the installed app with its private, pinned Python dependencies."""
from pathlib import Path
import runpy
import sys

APP_DIR = Path(__file__).resolve().parent
PREFIX = APP_DIR.parent.parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(PREFIX / "lib/my-notes/vendor"), str(APP_DIR)]
runpy.run_path(str(APP_DIR / "main.py"), run_name="__main__")
