"""Compare GFM mode with official extension examples (or --all examples)."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from markdown_engine import render_markdown, GFM_PARSER_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Also compare the older GFM spec's CommonMark examples")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    normalizer_spec = importlib.util.spec_from_file_location("normalize", ROOT / "tests/commonmark/normalize.py")
    normalizer = importlib.util.module_from_spec(normalizer_spec)
    normalizer_spec.loader.exec_module(normalizer)
    data = (ROOT / "tests/gfm/spec-0.29-gfm.json").read_bytes()
    examples = [e for e in json.loads(data) if args.all or "(extension)" in e["section"]]
    failures = []
    totals, passed = Counter(), Counter()
    for example in examples:
        totals[example["section"]] += 1
        actual = render_markdown(example["markdown"], gfm=True)
        if normalizer.normalize_html(actual) == normalizer.normalize_html(example["html"]):
            passed[example["section"]] += 1
        else:
            failures.append({**example, "actual": actual})
    report = {"specification": "GFM 0.29-gfm", "source": "https://github.github.com/gfm/",
              "fixture_sha256": hashlib.sha256(data).hexdigest(),
              "parser": f"cmarkgfm {GFM_PARSER_VERSION}",
              "scope": "All examples" if args.all else "Official extension sections",
              "total": len(examples), "passed": len(examples)-len(failures),
              "failed": len(failures), "failures": failures}
    print(f"GFM: {report['passed']}/{report['total']} passed; {len(failures)} failed")
    for section, total in totals.items():
        print(f"  {section}: {passed[section]}/{total}")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
