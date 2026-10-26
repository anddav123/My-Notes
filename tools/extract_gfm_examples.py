"""Extract official examples from the published GitHub GFM specification.

Preserves code text, converting the spec's visual tab arrows back to tabs.
Usage: python tools/extract_gfm_examples.py source.html output.json
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys


class Examples(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.examples = []
        self.section = ""
        self.heading = None
        self.example = None
        self.code = None
        self.text = []
        self.in_tab = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("h2", "h3"):
            self.heading = []
        if tag == "div" and attrs.get("class") == "example":
            self.example = {"example": int(attrs["id"].removeprefix("example-")),
                            "section": self.section}
        if tag == "code" and self.example is not None:
            self.code = {"language-markdown": "markdown", "language-html": "html"}.get(attrs.get("class"))
            self.text = []
        if tag == "span" and attrs.get("class") == "tab":
            self.in_tab = True

    def handle_data(self, data):
        if self.heading is not None:
            self.heading.append(data)
        if self.code:
            self.text.append("\t" if self.in_tab else data.replace("→", "\t"))

    def handle_endtag(self, tag):
        if tag in ("h2", "h3") and self.heading is not None:
            self.section = "".join(self.heading).strip()
            self.heading = None
        if tag == "span":
            self.in_tab = False
        if tag == "code" and self.code:
            self.example[self.code] = "".join(self.text)
            if self.code == "html":
                self.examples.append(self.example)
                self.example = None
            self.code = None


if __name__ == "__main__":
    parser = Examples()
    parser.feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
    parser.close()
    assert len(parser.examples) == 677
    assert [e["example"] for e in parser.examples] == list(range(1, 678))
    Path(sys.argv[2]).write_text(json.dumps(parser.examples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Extracted {len(parser.examples)} official examples")
