"""Bootstrap confidence intervals for report-generation metrics.

Reads a results.jsonl from evaluate_api.py, precomputes per-report finding
mentions and unigram F1, then resamples studies with replacement.

Usage:
  python test/bootstrap_ci.py test/results/medgemma500_t0/results.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from evaluate_api import LABELS, mentions, unigram_f1  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in pathlib.Path(args.results).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if row.get("status") == 200 and row.get("report")]
    if not rows:
        raise SystemExit("no successful reports")

    ref = {label: [] for label in LABELS}
    pred = {label: [] for label in LABELS}
    uf1 = []
    for row in rows:
        for label, pattern in LABELS.items():
            ref[label].append(mentions(row["findings"], pattern))
            pred[label].append(mentions(row["report"], pattern))
        uf1.append(unigram_f1(row["report"], row["findings"]))

    rng = random.Random(args.seed)
    n = len(rows)
    macro_samples = []
    unigram_samples = []
    label_samples = {label: [] for label in LABELS}
    for _ in range(args.bootstrap):
        indices = [rng.randrange(n) for _ in range(n)]
        scores = []
        for label in LABELS:
            tp = fp = fn = 0
            for i in indices:
                if ref[label][i] and pred[label][i]:
                    tp += 1
                elif pred[label][i]:
                    fp += 1
                elif ref[label][i]:
                    fn += 1
            score = f1(tp, fp, fn)
            scores.append(score)
            label_samples[label].append(score)
        macro_samples.append(statistics.mean(scores))
        unigram_samples.append(statistics.mean(uf1[i] for i in indices))

    def summary(samples):
        return {
            "mean": round(statistics.mean(samples), 4),
            "ci95": [round(percentile(samples, 0.025), 4),
                     round(percentile(samples, 0.975), 4)],
        }

    result = {
        "n": n,
        "bootstrap": args.bootstrap,
        "macro_f1": summary(macro_samples),
        "unigram_f1": summary(unigram_samples),
        "labels": {label: summary(values) for label, values in label_samples.items()},
    }
    out = pathlib.Path(args.results).with_name("bootstrap_ci.json")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
