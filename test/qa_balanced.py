"""Balanced yes/no QA evaluation (cardiomegaly, effusion).

The first 50 OpenI images are ~90 % negative, which makes raw accuracy
misleading. This script selects an equal number of reference-positive and
reference-negative studies per finding, asks the same question to the active
backend, and reports sensitivity, specificity, PPV, NPV and accuracy with
Wilson 95 % confidence intervals.

Run against each backend and save separate JSON files:
  python test/qa_balanced.py --api-key KEY --out test/results/qa_balanced_cxr.json
  python test/qa_balanced.py --api-key KEY --out test/results/qa_balanced_medgemma.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qa_test import QUESTIONS, answer_polarity  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "openi500"


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (round(max(0.0, centre - margin), 3), round(min(1.0, centre + margin), 3))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--per-label", type=int, default=30,
                        help="positives per finding; same number of negatives")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="test/results/qa_balanced.json")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key")

    data = pathlib.Path(args.data)
    metadata = [
        json.loads(line)
        for line in (data / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rng = random.Random(args.seed)

    plan = []
    for label, pattern in QUESTIONS.items():
        positives = [r for r in metadata if pattern.search(r["findings"])
                     and not _negated_reference(r["findings"], pattern)]
        negatives = [r for r in metadata if r not in positives]
        # Reference-positive rows that the crude regex calls negative are
        # ignored for the balanced set; this is a screening split, not a label.
        rng.shuffle(positives)
        rng.shuffle(negatives)
        n = min(args.per_label, len(positives), len(negatives))
        selected = [(r, True) for r in positives[:n]] + [(r, False) for r in negatives[:n]]
        rng.shuffle(selected)
        plan.append((label, selected))

    rows = []
    for label, selected in plan:
        question = (
            "Is there cardiomegaly?" if label == "cardiomegaly"
            else "Is there a pleural effusion?"
        )
        for record, truth in selected:
            started = time.time()
            with (data / record["file"]).open("rb") as handle:
                response = requests.post(
                    f"{args.base_url}/ask",
                    headers={"X-API-Key": args.api_key},
                    files={"file": (record["file"], handle, "image/jpeg")},
                    data={"question": question, "temperature": "0", "top_p": "1"},
                    timeout=300,
                )
            elapsed = time.time() - started
            body = response.json()
            answer = (body.get("answer") or "").strip()
            predicted = answer_polarity(answer)
            rows.append(
                {
                    "id": record["id"],
                    "label": label,
                    "reference_positive": truth,
                    "answer": answer,
                    "predicted_positive": predicted,
                    "status": response.status_code,
                    "latency_s": round(elapsed, 2),
                }
            )

    summary = {}
    for label in QUESTIONS:
        subset = [r for r in rows if r["label"] == label]
        tp = sum(1 for r in subset if r["reference_positive"] and r["predicted_positive"] is True)
        fn = sum(1 for r in subset if r["reference_positive"] and r["predicted_positive"] is not True)
        tn = sum(1 for r in subset if not r["reference_positive"] and r["predicted_positive"] is False)
        fp = sum(1 for r in subset if not r["reference_positive"] and r["predicted_positive"] is True)
        sensitivity = tp / (tp + fn) if tp + fn else 0.0
        specificity = tn / (tn + fp) if tn + fp else 0.0
        ppv = tp / (tp + fp) if tp + fp else 0.0
        npv = tn / (tn + fn) if tn + fn else 0.0
        accuracy = (tp + tn) / len(subset) if subset else 0.0
        summary[label] = {
            "n": len(subset),
            "tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "unknown": sum(1 for r in subset if r["predicted_positive"] is None),
            "sensitivity": round(sensitivity, 3),
            "specificity": round(specificity, 3),
            "ppv": round(ppv, 3),
            "npv": round(npv, 3),
            "accuracy": round(accuracy, 3),
            "sensitivity_ci": wilson(tp, tp + fn),
            "specificity_ci": wilson(tn, tn + fp),
            "accuracy_ci": wilson(tp + tn, len(subset)),
            "latency_mean_s": round(
                sum(r["latency_s"] for r in subset) / max(1, len(subset)), 2
            ),
        }

    result = {
        "dataset": str(data),
        "n_questions": len(rows),
        "per_label": summary,
        "rows": rows,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    print(f"wrote {out}")


def _negated_reference(text: str, pattern) -> bool:
    """Reuse the evaluate_api negation logic without importing the whole module."""
    from evaluate_api import negated

    return all(
        negated(text, match.start(), match.end())
        for match in pattern.finditer(text)
    )


if __name__ == "__main__":
    main()
