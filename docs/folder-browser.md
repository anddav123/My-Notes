# Folder browser

Choose **Open Folder…** from the main menu (Ctrl+Shift+O), or click **Folders**
in the toolbar. The left sidebar lists `.md` and `.markdown` files, including
uppercase extensions. Expand subfolders to browse their notes. F9 or the
Folders button shows or hides the sidebar. Its divider can be dragged to resize it.

Click a note to open it in the existing editor. If the current note is modified,
Save, Discard, or Cancel appears first. Cancel keeps the current note selected;
Save must succeed before switching. Failed opens preserve the current document
and its selection. Clicking the current note does not reload it.

Use the folder icon at the top of the sidebar to choose a different folder.
This changes the browser without replacing the current document. The refresh
button reloads the tree; filesystem watches also update expanded folders when
files are created, renamed, saved, or removed. Folder reads run in the background.
Directory symlinks are omitted to prevent recursive loops.

The chosen local folder and sidebar visibility are remembered per user in
`$XDG_STATE_HOME/MyNotes/folder-browser.json`, normally under `~/.local/state`.
Missing or unreadable folders show a message in the sidebar; use the folder
button to select another. Note contents are never stored in the browser settings.

Recent files, normal Open, and editor/preview controls remain available.
Future Debian builds include the module; existing packages were not rebuilt.

Integration checks:

    PYTHONPATH=. .venv/bin/python tests/check_folder_browser.py
