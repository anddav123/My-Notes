"""Run the official CommonMark 0.31.2 examples against My Notes' parser.

Exit status 1 means at least one example differs from the official output.
This checks Markdown-to-HTML parsing, not GTK display or browser behaviour.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIXTURES = ROOT / "tests" / "commonmark"


def main():
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("--legacy", action="store_true", help="Audit the former Python-Markdown configuration")
    args_parser.add_argument("--gfm", "--tables", dest="gfm", action="store_true",
                             help="Compare GFM mode instead of strict CommonMark (extensions can differ)")
    args_parser.add_argument("--report", type=Path, help="Write a JSON report including every mismatch")
    args = args_parser.parse_args()
    if args.legacy:
        import markdown
        engine = f"Python-Markdown {markdown.__version__} (former app configuration)"
        render = lambda source: markdown.markdown(source, extensions=["fenced_code", "sane_lists", "tables"])
    else:
        from markdown_engine import render_markdown, PARSER_VERSION, GFM_PARSER_VERSION
        engine = (f"cmarkgfm {GFM_PARSER_VERSION}, GFM" if args.gfm
                  else f"markdown-it-py {PARSER_VERSION}, CommonMark")
        render = lambda source: render_markdown(source, gfm=args.gfm)

    # The upstream normalizer ignores insignificant whitespace and HTML
    # serialization differences while preserving meaningful code whitespace.
    spec = importlib.util.spec_from_file_location("commonmark_normalize", FIXTURES / "normalize.py")
    normalizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(normalizer)
    fixture_bytes = (FIXTURES / "spec-0.31.2.json").read_bytes()
    examples = json.loads(fixture_bytes)
    failures = []
    sections = Counter()
    for example in examples:
        actual = render(example["markdown"])
        if normalizer.normalize_html(actual) != normalizer.normalize_html(example["html"]):
            failures.append({"example": example["example"], "section": example["section"],
                             "markdown": example["markdown"], "expected": example["html"],
                             "actual": actual})
            sections[example["section"]] += 1
    report = {
        "specification": "CommonMark 0.31.2",
        "fixture_source": "https://spec.commonmark.org/0.31.2/spec.json",
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "parser": engine, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(examples), "passed": len(examples) - len(failures),
        "failed": len(failures), "failed_by_section": dict(sections),
        "failures": failures,
        "scope": "Parser HTML output only; not full GTK preview conformance or certification.",
    }
    print(f"{engine}: {report['passed']}/{report['total']} passed; {report['failed']} failed")
    for section, count in sections.items():
        print(f"  {section}: {count} differences")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
