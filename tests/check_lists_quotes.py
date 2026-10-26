"""Structural and allocated-layout checks for CommonMark lists and quotes."""
from pathlib import Path
import time
from main import MyNotesApp, MyNotesWindow, Gio, GLib
from preview import parse_markdown


def plain(source):
    return "".join(text for text, _styles in parse_markdown(source, tables=False).runs)


tight = plain("- Alpha\n- Beta\n")
assert "• Alpha\n• Beta" in tight
loose = plain("- First paragraph\n\n  Second paragraph\n\n- Next item\n")
assert loose == "• First paragraph\n\nSecond paragraph\n\n• Next item\n\n", repr(loose)
assert "• \n" not in loose
assert plain("7. Seven\n8. Eight\n").startswith("7. Seven\n8. Eight")
assert "• \n• Nonempty" in plain("-\n- Nonempty\n")

source = '''Normal text.

- Parent item with enough text to wrap several times in the preview pane and verify the hanging indent remains aligned with the first word, including the additional continuation words at the end.
  - Child item
    - Grandchild item
  - Child sibling
- Root sibling

> Outer quote
>
> > Inner quote
>
> Outer continuation

> - Quoted list
>   - Nested quoted list

- First loose paragraph

  Later loose paragraph

- Next loose item

98. Ordered long item with enough text to wrap several times and check that the continuation line begins after the full number and punctuation rather than returning to the marker's left edge.
99. Next number

Ordinary ending.
'''
app = MyNotesApp()
app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
app.register(None)
w = MyNotesWindow(app)
w.buffer.set_text(source)
w.refresh_preview()
w.present()
deadline = time.monotonic() + .8
while time.monotonic() < deadline:
    GLib.MainContext.default().iteration(False)
    time.sleep(.005)
p = w.preview
b = p.get_buffer()
text = b.get_text(*b.get_bounds(), True)


def iterator(label):
    return b.get_iter_at_offset(text.index(label))


def x(label):
    return p.get_iter_location(iterator(label)).x


normal, parent, child, grandchild = (x(label) for label in
                                   ("Normal text", "Parent item", "Child item", "Grandchild item"))
assert normal < parent < child < grandchild, (normal, parent, child, grandchild)
assert x("Root sibling") == parent
assert x("Child sibling") == child
assert x("First loose paragraph") == x("Later loose paragraph") == x("Next loose item") == parent
assert normal < x("Outer quote") < x("Inner quote")
assert x("Outer continuation") == x("Outer quote")
assert x("Quoted list") > x("Outer quote")
assert x("Nested quoted list") > x("Quoted list")
assert x("Ordinary ending") == normal

for label in ("Parent item", "Ordered long item"):
    start = iterator(label)
    next_display = start.copy()
    assert p.forward_display_line(next_display)
    # Pango's fractional glyph advances can round the marker edge by one pixel.
    assert abs(p.get_iter_location(start).x - p.get_iter_location(next_display).x) <= 1, (
        label, p.get_iter_location(start).x, p.get_iter_location(next_display).x)

# Re-rendering removes old layout tags, rather than accumulating them forever.
names = list(p.layout_tags)
p.render("Normal paragraph")
assert not p.layout_tags
assert all(b.get_tag_table().lookup(name) is None for name in names)
w.destroy()
print("PASS: tight/loose spacing, ordered/empty items, nested lists/quotes, combined containers, actual wrapped-line alignment, margin restoration, cleanup")
