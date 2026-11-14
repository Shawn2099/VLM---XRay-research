"""Verifier gate: does DenseNet-121 actually predict the reference findings?

For every OpenI-500 study we compare DenseNet's image probabilities with CheXbert
labels taken from the *reference* radiology report. That gives a per-finding AUC,
a Youden threshold, sensitivity/specificity and PPV — the numbers the verdict
engine needs, and the evidence for guardrails G2/G3/G4.

Writes data_trustmed/calibration.json (thresholds + PPV) and docs/VERIFIER_GATE.md.

Run:  python -m trustmed.eval.verify_gate --limit 500
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict

from sklearn.metrics import roc_auc_score, roc_curve

from trustmed import config, db
from trustmed.services import classifier, findings

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "test" / "data" / "openi500"
OUT_MD = ROOT / "docs" / "VERIFIER_GATE.md"


def reference_labels(report: str, wanted: set[str]) -> dict[str, int]:
    """CheXbert on the reference report; +1 positive, 0 otherwise (blank/neg/uncertain)."""
    vector = findings._label_vector(report)
    out = {}
    for index, label in enumerate(findings.CHEXBERT_LABELS):
        if label not in wanted:
            continue
        raw = vector[index] if index < len(vector) else ""
        out[label] = 1 if raw not in ("", None) and int(raw) > 0 else 0
    return out


def youden_threshold(y_true: list[int], scores: list[float]) -> tuple[float, float, float]:
    if len(set(y_true)) < 2:
        return 0.5, 0.0, 0.0
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    best = max(range(len(thresholds)), key=lambda i: tpr[i] - fpr[i])
    threshold = float(thresholds[best])
    # recompute sens/spec at that threshold for clarity
    tp = sum(1 for y, s in zip(y_true, scores) if y == 1 and s >= threshold)
    fn = sum(1 for y, s in zip(y_true, scores) if y == 1 and s < threshold)
    fp = sum(1 for y, s in zip(y_true, scores) if y == 0 and s >= threshold)
    sens = tp / (tp + fn) if tp + fn else 0.0
    spec = 1 - fp / (fp + (len(y_true) - tp - fn - fp)) if (len(y_true) - tp - fn - fp) > 0 else 0.0
    return round(threshold, 3), round(sens, 3), round(spec, 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        records = records[: args.limit]

    wanted = set(classifier.XRV_TO_CHEXBERT.values())
    per_label: dict[str, dict[str, list]] = defaultdict(lambda: {"y": [], "p": []})

    for index, record in enumerate(records, 1):
        labels = reference_labels(record["findings"], wanted)
        probs = classifier.predict(str(DATA / record["file"]))
        for label, prob in probs.items():
            if label not in labels:
                continue
            per_label[label]["y"].append(labels[label])
            per_label[label]["p"].append(prob)
        if index % 50 == 0:
            print(f"  {index}/{len(records)}", flush=True)

    summary = {}
    for label, data in sorted(per_label.items()):
        y, p = data["y"], data["p"]
        positives = sum(y)
        if positives < 5 or positives == len(y):
            summary[label] = {
                "n": len(y), "positives": positives, "auc": None,
                "threshold": config.POSITIVE_THRESHOLD, "sens": None, "spec": None,
                "ppv": None, "verdict": "insufficient positives",
            }
            continue
        auc = float(roc_auc_score(y, p))
        threshold, sens, spec = youden_threshold(y, p)
        tp = sum(1 for yy, pp in zip(y, p) if yy == 1 and pp >= threshold)
        fp = sum(1 for yy, pp in zip(y, p) if yy == 0 and pp >= threshold)
        ppv = tp / (tp + fp) if tp + fp else 0.0
        summary[label] = {
            "n": len(y),
            "positives": positives,
            "auc": round(auc, 3),
            "threshold": threshold,
            "sens": sens,
            "spec": spec,
            "ppv": round(ppv, 3),
            "prevalence": round(positives / len(y), 3),
            "trusted": auc >= 0.80,
        }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": db.now(),
        "n_studies": len(records),
        "corpus": "openi500",
        "classifier": summary,
        "confidence": {"knots": []},
    }
    config.CALIBRATION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = [
        "| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, s in summary.items():
        if s["auc"] is None:
            rows.append(f"| {label} | {s['positives']}/{s['n']} | — | {s['threshold']} | — | — | — | no |")
        else:
            rows.append(
                f"| {label} | {s['positives']}/{s['n']} | {s['auc']:.3f} | {s['threshold']:.2f} | "
                f"{s['sens']:.2f} | {s['spec']:.2f} | {s['ppv']:.2f} | "
                f"{'yes' if s['trusted'] else 'no'} |"
            )

    trusted = [label for label, s in summary.items() if s.get("trusted")]
    header = [
        "# Verifier gate — DenseNet-121 vs CheXbert on the reference report",
        "",
        f"* studies: {len(records)} (OpenI-500)",
        f"* corpus: `test/data/openi500`",
        "* labels: CheXbert positive on the reference report = 1, everything else = 0",
        "* threshold: Youden J on the same data (reported as an upper bound, not a held-out estimate)",
        f"* trusted (AUC >= 0.80): **{', '.join(trusted) if trusted else 'none'}**",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(header + rows) + "\n", encoding="utf-8")

    print("\n".join(rows))
    print(f"\ntrusted: {trusted}")
    print(f"wrote {config.CALIBRATION_PATH} and {OUT_MD}")


if __name__ == "__main__":
    main()
