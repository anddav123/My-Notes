# Lists and blockquotes

## Tight nested lists

- Parent item with a deliberately long sentence to check that wrapped text lines up with the words after the bullet rather than returning to the left edge of the preview.
  - Child item
    - Grandchild item
  - Another child
- Root sibling

## Loose list: multiple paragraphs

- First paragraph stays beside its bullet.

  Second paragraph belongs to the same item and aligns with its text.

  - A nested child in a loose item

  Final paragraph returns to the parent indentation.

- Next item has a visible paragraph gap above it.

## Ordered and mixed lists

7. Numbering starts at seven.
8. The next item is eight.
   - A bullet inside an ordered item
     1. A number inside that bullet
     2. Another number
9. Back at the outer level.

## Nested blockquotes

> Outer quotation with a long sentence that wraps onto additional lines while keeping the whole quotation indented consistently.
>
> > Inner quotation has another level of indentation.
> >
> > Another paragraph at the inner level.
>
> Back to the outer quotation.

## Lists inside quotes

> - First quoted list item
>   - Nested quoted list item
> - Second quoted list item

## Quotes and code inside lists

- An item containing a quotation:

  > Quoted paragraph inside the list.
  >
  > Another quoted paragraph.

  A continuation paragraph belongs to the original list item.

- An item with code:

  ```python
  def greeting():
      return "Spacing inside code is preserved"
  ```

  Text after the code returns to the item indentation.

## Long list markers

98. A longer ordered-list marker with enough text to wrap across multiple display lines and check the hanging indentation of every continuation line.
99. Another item.
100. Three digits should still align wrapped text with the item content rather than its marker.

## Empty items

-
- Nonempty item after an empty one

## Ordinary paragraph

This paragraph returns to the normal left margin after all nested containers.
