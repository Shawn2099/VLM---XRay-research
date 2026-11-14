"""Recompute calibration from cached probabilities (no model inference).

    python -m trustmed.eval.recalibrate --probs data_trustmed/probs_ensemble.json \
        --out data_trustmed/calibration.json

Lets the threshold policy be changed and re-checked in seconds instead of
re-running three DenseNets over 500 images.
"""

from __future__ import annotations

import argparse
import json
import pathlib

from sklearn.metrics import roc_auc_score

from trustmed import config
from trustmed.eval.verify_gate import operating_points
from trustmed.services import verdict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probs", required=True)
    parser.add_argument("--out", default=str(config.CALIBRATION_PATH))
    parser.add_argument("--weights", default="ensemble")
    args = parser.parse_args()

    dump = json.loads(pathlib.Path(args.probs).read_text(encoding="utf-8"))
    per_label: dict[str, dict[str, list]] = {}
    for record in dump.values():
        for label, prob in record["probs"].items():
            entry = per_label.setdefault(label, {"y": [], "p": []})
            entry["y"].append(int(record["labels"].get(label, 0)))
            entry["p"].append(float(prob))

    summary = {}
    for label, data in sorted(per_label.items()):
        y, p = data["y"], data["p"]
        positives = sum(y)
        if positives < 5 or positives == len(y):
            summary[label] = {
                "n": len(y), "positives": positives, "auc": None,
                "trusted": False, "verdict": "insufficient positives",
            }
            continue
        auc = float(roc_auc_score(y, p))
        points = operating_points(y, p)
        summary[label] = {
            "n": len(y),
            "positives": positives,
            "prevalence": round(positives / len(y), 3),
            "auc": round(auc, 3),
            "trusted": auc >= 0.80,
            **points,
            "threshold": points.get("thr_pos"),
            "sens": points.get("sens_at_pos"),
            "spec": points.get("spec_at_pos"),
            "ppv": points.get("ppv_at_pos"),
        }

    payload = {
        "generated_at": "recalibrated",
        "n_studies": len(dump),
        "corpus": "openi500",
        "weights": args.weights,
        "classifier": summary,
        "confidence": {"knots": []},
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    full, advisory = verdict.gate()
    print(f"{'label':<28}{'auc':>6}{'thr_pos':>9}{'thr_neg':>9}{'ppv':>7}  tier")
    for label, stats in summary.items():
        if not stats.get("auc"):
            print(f"{label:<28}{'—':>6}{'—':>9}{'—':>9}{'—':>7}  not assessable")
            continue
        tier = "verified" if label in full else "advisory" if label in advisory else "not assessable"
        print(
            f"{label:<28}{stats['auc']:>6.3f}{stats.get('thr_pos', 0):>9.2f}"
            f"{stats.get('thr_neg', 0):>9.2f}{stats.get('ppv_at_pos') or 0:>7.2f}  {tier}"
        )
    print(f"\nverified: {sorted(full)}")
    print(f"advisory: {sorted(advisory)}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
