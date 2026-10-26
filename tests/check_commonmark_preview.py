"""GTK regression and smoke checks; this is not full visual conformance."""
import json
from pathlib import Path

from main import MyNotesApp, MyNotesWindow, Gio
from preview import parse_markdown


def plain(source):
    return "".join(text for text, _styles in parse_markdown(source, tables=False).runs)


assert plain("7. seven\n8. eight\n").startswith("7. seven\n8. eight")
assert "a  b" in plain("`a  b`\n")
assert "a\u00a0b" in plain("a&nbsp;b\n")
assert "\t" in plain("    foo\tbar\n")
assert "print(1)" in plain("- item\n\n  ```python\n  print(1)\n  ```\n")
assert "\n" in plain("foo\\\nbar\n")

table = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
assert not parse_markdown(table, tables=False).tables
assert len(parse_markdown(table, tables=True).tables) == 1

app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
window = MyNotesWindow(app)
window.buffer.set_text(table)
window.refresh_preview()
assert len(window.preview.table_widgets) == 1
window.lookup_action("gfm").activate(None)
assert not window.preview.table_widgets
assert window.text() == table and window.buffer.get_modified()
window.lookup_action("gfm").activate(None)
assert len(window.preview.table_widgets) == 1

fixtures = Path(__file__).parent / "commonmark" / "spec-0.31.2.json"
examples = json.loads(fixtures.read_text(encoding="utf-8"))
for example in examples:
    try:
        window.preview.render(example["markdown"], tables=False)
    except Exception as error:
        raise AssertionError(f"GTK rendering crashed on official example {example['example']}") from error
window.destroy()
print(f"PASS: ordered starts, code spacing, nonbreaking spaces, nested fences, optional tables; {len(examples)} GTK smoke cases")
