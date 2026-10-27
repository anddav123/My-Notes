# My Notes

A Python GTK4/Libadwaita Markdown editor for GNOME.

## Machine-wide Debian package

A Debian 13 amd64 package can be built with `python3 tools/build_deb.py`.
The initial version is `0.1.0-1`. It installs the app, private pinned dependencies,
GNOME launcher and icon system-wide while keeping notes/preferences per user.
See [packaging/README.md](packaging/README.md) for installation, switching from
the development launcher, verification, source archives and supported platforms.

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

## App icon and GNOME launcher

Install the per-user launcher after setting up the project environment:

```bash
.venv/bin/python tools/install_desktop.py
```

My Notes then appears in GNOME's app grid. Search for **My Notes** to launch it,
or right-click its app-grid icon and choose **Pin to Dash** (wording may vary)
to keep it in the dock. The launcher uses this checkout's `run.sh` and tested
Python environment; no terminal window or administrator permissions are needed.
Close and reopen a running instance to pick up its new icon.

The approved notebook/MY-arrow artwork is stored as a scalable SVG in
`data/icons/hicolor/scalable/apps/`. The launcher template is in `data/`.
The installer copies both into your user application/icon directories and
can be rerun after icon changes or after moving the checkout. It deliberately
does not register Markdown file associations yet; it launches the application.

## Markdown source editing

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

The preview updates shortly after typing stops. The linked **Editor | Preview**
buttons select three layouts: Editor only, Editor & preview, or Preview only.
Turn either pane on or off; the last visible pane stays on to avoid an empty
window. `Ctrl+Shift+P` cycles through all three layouts. When both are visible,
drag the divider to adjust the widths; its position is remembered when returning
from a single-pane view. Switching views preserves the note and unsaved changes.

The native GTK preview renders headings, bold and italic text, lists,
blockquotes, inline and fenced code, and tables. Links are clickable, and
images render in the preview. Rendering does not run scripts. Remote images
load only after you click **Load image**. Raw HTML is not a full browser layout.
Syntax highlighting and the file organiser remain future work.

## CommonMark compatibility

With **Preferences → Markdown → GitHub Flavoured Markdown (GFM)** turned off, the parser uses
markdown-it-py in its tested CommonMark configuration. With it turned on,
GitHub's reference parser enables all five GFM extensions together. The status
bar shows the current mode. GFM is enabled initially and the choice is saved per user.

## Undo and redo

Use **Undo** and **Redo** in the menu, or **Ctrl+Z** to undo and
**Ctrl+Shift+Z / Ctrl+Y** to redo. Commands are unavailable when their respective
history is empty and are disabled during file operations.

GTK groups ordinary typing/deletion into native undo steps. Each Replace and
the whole Replace All operation form explicit single steps. Search, selection
and view changes do not create document edits. Saving keeps edit history;
New and Open clear it so history cannot cross document boundaries. A fresh edit
after Undo discards the unused Redo branch.

Undo/Redo from Preview-only mode reveals the editor alongside the preview.
The preview and unsaved-change indicator follow the result. Search and
replacement text fields keep their own native text undo when focused.

## Find and replace

Use **Find…** or **Find and Replace…** in the menu:

- **Ctrl+F**: open Find and focus the search field.
- **Ctrl+H**: open Find and Replace.
- **Enter / Shift+Enter** in the search field: next / previous match.
- **F3 / Shift+F3** or **Ctrl+G / Ctrl+Shift+G**: next / previous match.
- **Esc** in the search panel: close it and return to the editor.

Matches are highlighted in the Markdown source with a current/total count.
Search wraps at the start/end of the document. **Match case** switches between
case-insensitive and case-sensitive matching. Searches and replacement text
are literal; regular expressions and replacement escape sequences are not used.

**Replace** changes the selected match, then selects the following one.
If the source selection has moved elsewhere, the first Replace locates the
next match without changing unrelated text. **Replace All** changes every
non-overlapping match once; it does not recursively replace newly inserted text.
An empty replacement deletes matches. Changes update the preview and mark the
note as modified. In the editor, **Ctrl+Z** undoes a replacement operation or an
entire Replace All operation in one step.

Opening search in Preview-only mode shows the editor alongside the preview.
The search field receives focus, and the preview remains visible. Hiding the
editor closes its search panel. Closing search does not revert the viewing mode.
Opening a different note or creating a new one clears undo history so an old
document cannot be restored accidentally into the new document.

## Preferences

Open **Preferences** from the menu or press `Ctrl+,`. On **Appearance**, under **Toolbar**, choose
**Text** (the default) or **Icons**. New, Open, Save, Editor and Preview update
immediately, including in other open windows. Icon buttons retain their
tooltips, accessible labels, keyboard shortcuts and toggle states.

The choice is saved per user in `$XDG_CONFIG_HOME/MyNotes/preferences.json`
(normally `~/.config/MyNotes/preferences.json`) and restored at the next launch.
It does not change note files. Invalid settings fall back to Text; a failed
save is reported without changing the current preference.

## GitHub Flavored Markdown

GFM mode adds tables, task lists, single/double-tilde strikethrough, automatic
links for bare URLs and email addresses, and GFM's disallowed-HTML tag filter.
Turn the switch off in **Preferences → Markdown** to restore core CommonMark interpretation of all
these features at once. The source is never rewritten by the switch.

Tasks use `- [ ]` for incomplete and `- [x]` or `- [X]` for complete. Preview
checkboxes are read-only; edit the marker in the source to change task state.
Use `~~removed~~` or `~removed~` for strikethrough. Code spans and code blocks
keep all of this syntax literal.

Open `examples/gfm-demo.md` to compare modes. The GFM extension audit passes
26 of 28 published examples; two unusual XMPP resource-path cases differ in
the reference library. See `docs/gfm-audit.md` for exact scope and results.
This does not constitute full GFM conformance or all GitHub.com features.

Parser compliance and GTK preview completeness are separate. The official
Markdown-to-HTML tests verify the parser. Raw HTML still has limited
native rendering. Passing the parser tests does not certify full preview
conformance. See `docs/commonmark-audit.md` for measured results and limitations.

## Lists and blockquotes

Nested lists and blockquotes use paragraph margins for each nesting level.
Wrapped list text uses a hanging indent aligned with the item content, and
ordered markers reserve space for their actual displayed width. Tight lists
keep adjacent items together; loose lists preserve paragraph gaps without
separating the first paragraph from its bullet. Continuation paragraphs return
to their parent item's margin after a nested list, quote, or code block.

Open `examples/lists-quotes-demo.md` for mixed lists, nested quotations, code,
empty items, and longer ordered markers. These are core CommonMark features
and work with the GFM extension switch off. A focused test measures actual
GTK text positions and wrapped-line alignment in a displayed window.

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

HTTP, HTTPS, mailto, XMPP and file destinations are supported. Unsupported schemes
produce a message. Open `examples/links-demo.md` to try the feature.

## Images

Use `![Description](path/to/image.png "Optional title")`. Local images load
automatically, with relative paths resolved from the saved note's folder.
Save an untitled note first to resolve relative images. File URLs,
reference-style images, images inside tables, and images wrapped in links
are supported. Save As refreshes the preview against the new folder.

Images are loaded in the background, keep their aspect ratio, and are reduced
to at most 480 × 320 pixels (160 × 120 inside tables). The available preview
width may reduce the image further when it is rendered. Supported formats
depend on GdkPixbuf; PNG, JPEG and SVG work on the development VM. Animated
formats display a static frame.

HTTP and HTTPS images show **Load image** first. Clicking it allows that URL
for this preview session, and recently loaded images are cached in memory.
There is a 10 MB limit per source image and a network timeout. Missing,
unsupported or unreadable images show their description and an error tooltip.
Alt descriptions remain available to assistive technology for loaded images.
Open `examples/images-demo.md` to try the included local sample.

GTK 4.18 may log `Trying to snapshot GtkGizmo ... without a current allocation`
during rapid scrolling or resizing. This was traced to a scrollbar and remains
unresolved; image/editor regression checks pass despite the warning.

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
PYTHONPATH=. .venv/bin/python tests/check_images.py
PYTHONPATH=. .venv/bin/python tests/check_lists_quotes.py
PYTHONPATH=. .venv/bin/python tests/check_gfm.py
PYTHONPATH=. .venv/bin/python tests/check_view_modes.py
PYTHONPATH=. .venv/bin/python tests/check_preferences.py
PYTHONPATH=. .venv/bin/python tests/check_find_replace.py
PYTHONPATH=. .venv/bin/python tests/check_undo_redo.py
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
