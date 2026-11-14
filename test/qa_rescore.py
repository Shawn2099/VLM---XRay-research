"""Re-score stored QA results with the current polarity parser.

Usage: python test/qa_rescore.py test/results/qa50.json test/results/medgemma_qa50.json
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qa_test import QUESTIONS, answer_polarity  # noqa: E402


def main() -> None:
    for name in sys.argv[1:]:
        path = pathlib.Path(name)
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data["rows"]
        for row in rows:
            row["predicted_positive"] = answer_polarity(row["answer"])
            row["correct"] = row["predicted_positive"] == row["reference_positive"]

        correct = sum(1 for row in rows if row["correct"])
        per_label = {}
        for label in QUESTIONS:
            subset = [row for row in rows if row["label"] == label]
            per_label[label] = {
                "n": len(subset),
                "accuracy": round(
                    sum(r["correct"] for r in subset) / max(1, len(subset)), 3
                ),
                "reference_positive": sum(1 for r in subset if r["reference_positive"]),
                "polarity_unknown": sum(
                    1 for r in subset if r["predicted_positive"] is None
                ),
            }
        summary = {
            "n_questions": len(rows),
            "accuracy": round(correct / max(1, len(rows)), 3),
            "per_label": per_label,
            "rows": rows,
        }
        out = path.with_name(path.stem + "_rescored.json")
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(path.name, "->", out.name)
        print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
