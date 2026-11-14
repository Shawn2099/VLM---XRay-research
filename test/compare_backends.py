"""Compare two or more backend evaluation summaries produced by evaluate_api.py.

Usage:
  python test/compare_backends.py test/results/report_t0/summary.json \
      test/results/medgemma_t0/summary.json
"""

from __future__ import annotations

import json
import pathlib
import sys

METRICS = [
    ("n", "images"),
    ("ok", "successful"),
    ("latency_s", "latency"),
    ("report_words", "report words"),
    ("repetition_8gram", "repetition"),
    ("unigram_f1", "unigram F1"),
    ("macro_f1", "macro F1"),
    ("micro", "micro P/R"),
]


def fmt(value) -> str:
    if isinstance(value, dict):
        if "mean" in value:
            return f"mean {value['mean']} | p95 {value.get('p95', '?')} | max {value.get('max', '?')}"
        if "precision" in value:
            return f"P {value['precision']} / R {value['recall']}"
        if "min" in value:
            return f"mean {value['mean']} ({value['min']}-{value['max']})"
    return str(value)


def main() -> None:
    paths = [pathlib.Path(p) for p in sys.argv[1:]]
    if len(paths) < 2:
        raise SystemExit(__doc__)
    summaries = []
    for path in paths:
        data = json.loads(path.read_text())
        summaries.append((path.parent.name, data))

    names = [name for name, _ in summaries]
    lines = ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for key, label in METRICS:
        cells = []
        for _, data in summaries:
            value = data.get(key)
            if key == "report_words":
                value = data.get("report_words")
            cells.append(fmt(value))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    labels = sorted({label for _, data in summaries for label in data.get("labels", {})})
    lines += ["", "| finding F1 | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label in labels:
        cells = [str(data.get("labels", {}).get(label, {}).get("f1", "–")) for _, data in summaries]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    output = "\n".join(lines)
    print(output)
    out = pathlib.Path("test/results/compare.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output + "\n", encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
