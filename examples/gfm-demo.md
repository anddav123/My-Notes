# GFM preview demo

Use **Preferences → Markdown → GitHub Flavoured Markdown (GFM)** to compare modes.
Turning it off restores core CommonMark interpretation for all these features.

## Task lists

- [ ] An unfinished task
- [x] A completed task
- [X] Uppercase X also means completed
  - [ ] A nested task
  - [x] A completed nested task with **bold** text
- [ ] A long task description that should wrap neatly beneath the text, rather than returning to the checkbox at the beginning of every display line in the preview.

Preview checkboxes show the source state. Edit `[ ]` and `[x]` in the editor
to change a task; the preview is read-only.

## Strikethrough

~~Removed text~~ and ~also removed~.

~~**Bold removed text**~~ can combine formatting.

Three tildes are literal here: ~~~not removed~~~.

## Automatic links

https://example.org

www.example.org

hello@example.org

Inline code remains literal: `https://example.org` and `~~not removed~~`.

## Tables

| Task | Notes |
| :--- | :--- |
| ~~Old plan~~ | Use the new plan |
| **Website** | https://example.org |

## Code stays code

```markdown
- [x] Literal checkbox syntax
~~Literal strikethrough syntax~~
www.example.org
```

## Filtered raw HTML

GFM displays disallowed tags as text rather than interpreting them:

<script>this is displayed, not executed</script>
