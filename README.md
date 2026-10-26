# My Notes

A Python GTK4/Libadwaita Markdown editor for GNOME.

## Run on Debian 13

Install the runtime dependencies:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

From the project folder, run:

```bash
python3 main.py
```

Requires GTK 4.10 or later and Libadwaita 1.5 or later. Debian 13 supplies
compatible versions. No pip dependencies are required.

## Milestone 2: Markdown source editing

- Wrapped, monospace Markdown text editor with word and character counts.
- New (`Ctrl+N`), Open (`Ctrl+O`), Save (`Ctrl+S`), and Save As
  (`Ctrl+Shift+S`, also available in the menu).
- UTF-8 Markdown and text files; the file chooser also allows other extensions.
- Unsaved-change indicator and Save / Discard / Cancel prompt before New,
  Open, or closing the window.
- Failed or cancelled saves keep the current note open and modified.
- Asynchronous file I/O and detection of external changes before overwriting
  the current file. Use Save As to preserve a separate copy after a conflict.

This milestone edits Markdown source. Rendered preview, syntax highlighting,
and the file organiser are future work. Unsaved notes are not recovered after
a crash; save regularly. Save As defaults to `Untitled.md`; custom filenames
are used exactly as entered.

## Verify

Inside a GNOME desktop session, run:

```bash
PYTHONPATH=. python3 tests/check_editor.py
```

The integration check uses temporary files to exercise Unicode round trips,
modified state, external-edit conflicts, invalid text, and the unsaved-change
response handlers. It needs a graphical display.

For a manual check, type a note, save and reopen it, then test New/Open/Close
with unsaved changes. Check Cancel in both file choosers and the unsaved-change
prompt, plus Save As and the keyboard shortcuts.
