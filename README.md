# My Notes

A Python GTK4/Libadwaita Markdown editor for GNOME.

## Run on Debian 13

Install the runtime dependencies:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-markdown
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

Unsaved notes are not recovered after
a crash; save regularly. Save As defaults to `Untitled.md`; custom filenames
are used exactly as entered.

## Live Markdown preview

The preview appears beside the editor and updates shortly after typing stops.
Drag the divider to adjust the pane widths. Use the **Preview** button, the
**Show Preview** menu item, or `Ctrl+Shift+P` to show or hide it.

The native GTK preview renders headings, bold and italic text, lists,
blockquotes, inline and fenced code, and tables. Link destinations are shown
as text, and images appear as descriptions. It does not run scripts, fetch
remote content, or open links. Raw HTML is not a full browser layout.
Syntax highlighting, rendered images, and the file organiser remain future work.

Tables support formatted cells and column alignment:

Copy only the pipe-delimited rows below into a note. Do not include the
opening and closing backtick fences: those deliberately display source code
instead of a rendered table. Open `examples/preview-demo.md` in My Notes to
compare a rendered table and a fenced code example side by side.

```markdown
| Item | Quantity | Status |
| :--- | ---: | :---: |
| **Pens** | 3 | Ready |
| Paper | 10 | Ordered |
```

The colons select left, right, or centre alignment. Wide tables can be scrolled
horizontally in the preview pane.

## Verify

Inside a GNOME desktop session, run:

```bash
PYTHONPATH=. python3 tests/check_editor.py
PYTHONPATH=. python3 tests/check_preview.py
```

The integration check uses temporary files to exercise Unicode round trips,
modified state, external-edit conflicts, invalid text, and the unsaved-change
response handlers. It needs a graphical display.

For a manual check, type a note, save and reopen it, then test New/Open/Close
with unsaved changes. Check Cancel in both file choosers and the unsaved-change
prompt, plus Save As and the keyboard shortcuts.
Also check the live preview and table example, resize the divider, and toggle
the preview off and back on after making an edit.
