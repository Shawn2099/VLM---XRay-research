"""Paired bootstrap comparison of two models on the same studies.

The unpaired CIs in bootstrap_ci.py can overlap even when the paired difference
is consistent. This script resamples studies, computes macro F1 and unigram F1
for both models on the same resample, and reports the difference CI and a
two-sided bootstrap p-value.

Usage:
  python test/paired_bootstrap.py \
      test/results/cxr500_t0/results.jsonl \
      test/results/medgemma500_t0/results.jsonl
"""

from __future__ import annotations

import json
import pathlib
import random
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from evaluate_api import LABELS, mentions, unigram_f1  # noqa: E402


def f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def percentile(values, fraction):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def load(path):
    return {
        row["id"]: row
        for row in (
            json.loads(line)
            for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if row.get("status") == 200 and row.get("report")
    }


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    left_name = pathlib.Path(sys.argv[1]).parent.name
    right_name = pathlib.Path(sys.argv[2]).parent.name
    left = load(sys.argv[1])
    right = load(sys.argv[2])
    ids = sorted(set(left) & set(right))
    if not ids:
        raise SystemExit("no common successful IDs")

    ref = {label: [] for label in LABELS}
    left_pred = {label: [] for label in LABELS}
    right_pred = {label: [] for label in LABELS}
    left_uf1, right_uf1 = [], []
    for study_id in ids:
        reference = left[study_id]["findings"]
        for label, pattern in LABELS.items():
            ref[label].append(mentions(reference, pattern))
            left_pred[label].append(mentions(left[study_id]["report"], pattern))
            right_pred[label].append(mentions(right[study_id]["report"], pattern))
        left_uf1.append(unigram_f1(left[study_id]["report"], reference))
        right_uf1.append(unigram_f1(right[study_id]["report"], reference))

    def macro(pred, indices):
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
            scores.append(f1(tp, fp, fn))
        return statistics.mean(scores)

    rng = random.Random(0)
    n = len(ids)
    macro_diffs, unigram_diffs = [], []
    label_diffs = {label: [] for label in LABELS}
    for _ in range(1000):
        indices = [rng.randrange(n) for _ in range(n)]
        lm, rm = macro(left_pred, indices), macro(right_pred, indices)
        macro_diffs.append(rm - lm)
        unigram_diffs.append(
            statistics.mean(right_uf1[i] for i in indices)
            - statistics.mean(left_uf1[i] for i in indices)
        )
        for label in LABELS:
            def lab_score(pred):
                tp = fp = fn = 0
                for i in indices:
                    if ref[label][i] and pred[label][i]:
                        tp += 1
                    elif pred[label][i]:
                        fp += 1
                    elif ref[label][i]:
                        fn += 1
                return f1(tp, fp, fn)
            label_diffs[label].append(lab_score(right_pred) - lab_score(left_pred))

    def summarize(values):
        low = percentile(values, 0.025)
        high = percentile(values, 0.975)
        p = 2 * min(
            sum(1 for v in values if v <= 0) / len(values),
            sum(1 for v in values if v >= 0) / len(values),
        )
        return {
            "mean_difference": round(statistics.mean(values), 4),
            "ci95": [round(low, 4), round(high, 4)],
            "p_bootstrap": round(min(1.0, p), 4),
            "significant": not (low <= 0 <= high),
        }

    result = {
        "left": left_name,
        "right": right_name,
        "n": n,
        "macro_f1": summarize(macro_diffs),
        "unigram_f1": summarize(unigram_diffs),
        "labels": {label: summarize(values) for label, values in label_diffs.items()},
    }
    out = pathlib.Path("test/results/paired_bootstrap.json")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
