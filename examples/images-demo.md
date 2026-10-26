# Image preview demo

## Local image

![My Notes sample illustration](assets/sample-image.svg "A local image, scaled to fit the preview")

The image path is relative to this saved note. Images keep their proportions
and are reduced to fit the preview's image-size limit.

## Reference-style image

![The same sample, using a reference][sample]

[sample]: assets/sample-image.svg "Reference image title"

## Linked image

Click the image below to open the example website:

[![Open example.org](assets/sample-image.svg)](https://example.org)

## Image in a table

| Image | Description |
| :--- | :--- |
| ![Small sample](assets/sample-image.svg) | A thumbnail inside a table cell |

## Missing image

![This alt text remains visible](assets/not-present.png)

## Syntax

This fenced example displays the syntax without loading an image:

```markdown
![Description](path/to/image.png "Optional title")
```

For an HTTP or HTTPS image destination, click **Load image** to fetch it.
Remote images never load automatically the first time they appear.
