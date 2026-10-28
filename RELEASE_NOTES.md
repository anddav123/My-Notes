# My Notes 0.1.0

My Notes is a Markdown notes editor for GNOME, built with Python, GTK4 and
Libadwaita. This initial release targets Debian 13 and Anddav OS on amd64.

## Included

- Edit local Markdown files with a native live preview.
- Switch between editor-only, split and preview-only views.
- Browse Markdown notes in a folder sidebar with expandable subfolders.
- Create new notes without overwriting existing files.
- Search the five most recently opened or saved notes.
- Find and replace text, with undo and redo.
- Use CommonMark or enable GitHub Flavoured Markdown extensions for tables,
  task lists, strikethrough and automatic links.
- Preview links and local images; load remote images when requested.
- Choose text or icon toolbar buttons and remember preferences per user.
- Save, Discard or Cancel before switching away from a modified note.

## Compatibility and limitations

The core parser passes all 652 official CommonMark 0.31.2 examples. Native
preview rendering is separate from parser conformance: arbitrary HTML and some
layout details remain limited. GFM support has documented differences and is
not claimed to be fully conformant. See `docs/commonmark-audit.md` and
`docs/gfm-audit.md` for details.

The Debian package targets Python 3.13 and amd64; it is not intended for Debian
12 or other architectures. There is no automatic unsaved-note recovery yet.
An occasional GTK scrollbar allocation warning remains documented.

Packaging revisions such as `0.1.0-4` refine distribution metadata while the
application release remains 0.1.0. Repository publication is a separate step;
these notes do not imply that the public repository is already enabled.
