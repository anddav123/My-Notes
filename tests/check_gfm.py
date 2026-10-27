from pathlib import Path
import tempfile
"""GTK GFM feature and mode-switch regression tests."""
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib
from preview import parse_markdown
from markdown_engine import render_markdown

source = '''- [ ] Pending
- [x] Completed
  - [X] Nested done
- [ ] Long task description with many words to make this task wrap across multiple display lines and check the alignment of the continuation text after the native checkbox.

~~Removed~~ and ~also removed~ and ~~~literal~~~.

https://example.org www.example.org hello@example.org

| Item | Notes |
| --- | --- |
| ~~Old~~ | www.example.org |

`~~code~~ https://example.org`

```markdown
- [x] Literal task
```
'''
p = parse_markdown(source, gfm=True)
assert list(p.tasks.values()) == [False, True, True, False]
assert len(p.tables) == 1
assert any('strike' in styles and text == 'Removed' for text, styles in p.runs)
assert any('strike' in styles and text == 'also removed' for text, styles in p.runs)
assert any('~~~literal~~~' in text and 'strike' not in styles for text, styles in p.runs)
assert any(href == 'https://example.org' for href, _title in p.links.values())
assert any(href == 'http://www.example.org' for href, _title in p.links.values())
assert any(href == 'mailto:hello@example.org' for href, _title in p.links.values())
assert '<script>' not in render_markdown('<script>no execution</script>', gfm=True)
assert '&lt;script>' in render_markdown('<script>no execution</script>', gfm=True)
strict = parse_markdown(source, gfm=False)
assert not strict.tasks and not strict.tables and not strict.links
assert not any('strike' in styles for _text, styles in strict.runs)

test_preferences = tempfile.TemporaryDirectory(prefix="my-notes-test-")
app = MyNotesApp(preferences_path=Path(test_preferences.name) / "preferences.json")
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
w.buffer.set_text(source)
w.refresh_preview()
w.present()
deadline = time.monotonic() + .7
while time.monotonic() < deadline:
    GLib.MainContext.default().iteration(False)
    time.sleep(.005)
preview = w.preview
assert [box.get_active() for box in preview.task_widgets] == [False, True, True, False]
assert all(not box.get_sensitive() for box in preview.task_widgets)
assert all(box.get_width() > 0 for box in preview.task_widgets)
buffer = preview.get_buffer()
text = buffer.get_slice(*buffer.get_bounds(), True)
assert '• Pending' not in text  # The checkbox replaces the list bullet.
start = buffer.get_iter_at_offset(text.index('Long task'))
next_line = start.copy()
assert preview.forward_display_line(next_line)
assert abs(preview.get_iter_location(start).x - preview.get_iter_location(next_line).x) <= 1
old_box = preview.task_widgets[0]
assert w.lookup_action('gfm').get_state().get_boolean()
w.lookup_action('gfm').activate(None)
assert not preview.task_widgets and not preview.table_widgets
assert old_box.get_parent() is None
assert not preview.links
assert w.text() == source and w.buffer.get_modified()
w.lookup_action('gfm').activate(None)
assert len(preview.task_widgets) == 4 and len(preview.table_widgets) == 1
table_label = preview.table_widgets[0].get_child_at(0, 1).get_child()
assert table_label.get_text() == 'Old'
assert '<s>Old</s>' in table_label.get_label()
w.destroy()
print('PASS: native task states/nesting, single/double strike, bare web/email links, code exclusions, tagfilter, checkbox wrapping, all-feature mode toggle, table formatting, source preservation')
