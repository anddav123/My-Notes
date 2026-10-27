# Recent notes

The Open dropdown shows up to five successfully opened or saved local files,
most recent first. Search matches filenames and folder paths. Press Enter
to open the first match, or use the folder button to browse for another file.
Ctrl+O continues to open the file chooser directly.

The cross beside an entry removes it from history; it never deletes the file.
Unsaved changes still prompt before another note opens. A missing or unreadable
file shows an error and leaves the current document intact. Failed or cancelled
operations do not add history entries.

History contains file URIs only, not note contents. It is saved per user in
`$XDG_STATE_HOME/MyNotes/recent-notes.json` (normally
`~/.local/state/MyNotes/recent-notes.json`). It survives restarts and is independent
of button style and Markdown preferences. Existing files appear after they are
opened or saved with this version; history starts empty.

Run the focused GTK integration checks from the project directory:

    PYTHONPATH=. .venv/bin/python tests/check_recent_notes.py

The Debian build includes this module in future packages. Existing package
artifacts have not been rebuilt.
