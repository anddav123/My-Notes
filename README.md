# My Notes

A Python GTK4/Libadwaita Markdown editor for GNOME.

## Run on Debian 13

Install the runtime dependencies:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-venv
```

From the project folder, run:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
sh run.sh
```

Requires GTK 4.10 or later and Libadwaita 1.5 or later. Debian 13 supplies
compatible versions. The project environment shares Debian's GTK bindings and
pins its Markdown parser separately. After initial setup, use `sh run.sh` to
launch My Notes. Running `python3 main.py` bypasses the tested environment.

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
blockquotes, inline and fenced code, and tables. Links are clickable, and
images appear as descriptions. Rendering does not run scripts or fetch
remote content. Raw HTML is not a full browser layout.
Syntax highlighting, rendered images, and the file organiser remain future work.

## CommonMark compatibility

The parser uses markdown-it-py in its CommonMark configuration. The optional
**Enable GitHub Flavored Markdown (GFM)** menu setting is enabled initially to preserve table
previews; turn it off to use core CommonMark syntax without the table extension.

Parser compliance and GTK preview completeness are separate. The official
Markdown-to-HTML tests verify the parser. Images remain descriptions and raw HTML has limited
native rendering. Passing the parser tests does not certify full preview
conformance. See `docs/commonmark-audit.md` for measured results and limitations.

## Links

Click a link in the preview to open it. Web links use your default browser,
email links use the default mail application, and file links use the file's
default application. Inline links, reference links, angle-bracket autolinks,
and links in table cells are supported. Link labels keep their formatting;
hover over a link to see its destination and optional title.

Relative links such as `[Readme](../README.md)` resolve from the saved note's
folder, including after Save As. Save an untitled note before opening a relative
link. Links never open automatically while typing or selecting text.

In the main preview text, place the caret in a link and press `Ctrl+Enter` to
open it from the keyboard. Table links use GTK's native keyboard link controls.
Local `#heading-name` links scroll to matching headings (lowercase words joined
with hyphens; duplicate headings receive `-1`, `-2`, etc.). Heading anchors are
an application convenience rather than a CommonMark syntax requirement.

HTTP, HTTPS, mailto and file destinations are supported. Unsupported schemes
produce a message. Open `examples/links-demo.md` to try the feature.

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
PYTHONPATH=. .venv/bin/python tests/check_editor.py
PYTHONPATH=. .venv/bin/python tests/check_preview.py
PYTHONPATH=. .venv/bin/python tests/check_table_layout.py
PYTHONPATH=. .venv/bin/python tests/check_links.py
.venv/bin/python tests/check_commonmark.py
PYTHONPATH=. .venv/bin/python tests/check_commonmark_preview.py
```

The integration check uses temporary files to exercise Unicode round trips,
modified state, external-edit conflicts, invalid text, and the unsaved-change
response handlers. It needs a graphical display.

For a manual check, type a note, save and reopen it, then test New/Open/Close
with unsaved changes. Check Cancel in both file choosers and the unsaved-change
prompt, plus Save As and the keyboard shortcuts.
Also check the live preview and table example, resize the divider, and toggle
the preview off and back on after making an edit.
