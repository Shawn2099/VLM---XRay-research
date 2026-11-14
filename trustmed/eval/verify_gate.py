"""Verifier gate: does DenseNet-121 actually predict the reference findings?

For every OpenI-500 study we compare DenseNet's image probabilities with CheXbert
labels taken from the *reference* radiology report. That gives a per-finding AUC,
a Youden threshold, sensitivity/specificity and PPV â€” the numbers the verdict
engine needs, and the evidence for guardrails G2/G3/G4.

Writes data_trustmed/calibration.json (thresholds + PPV) and docs/VERIFIER_GATE.md.

Run:  python -m trustmed.eval.verify_gate --limit 500
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import defaultdict

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve

from trustmed import config, db
from trustmed.services import classifier, findings

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "test" / "data" / "openi500"
OUT_MD = ROOT / "docs" / "VERIFIER_GATE.md"


def symmetry(path: pathlib.Path) -> float:
    """Correlation with the horizontal mirror; laterals score low, frontals high."""
    array = np.asarray(Image.open(path).convert("L").resize((224, 224)), dtype=np.float32)
    array = (array - array.mean()) / (array.std() + 1e-6)
    return float((array * array[:, ::-1]).mean())


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


def operating_points(y_true: list[int], scores: list[float]) -> dict:
    """Two thresholds at 95 % confidence in each direction.

    t_pos: lowest score whose specificity is >= 0.95  -> safe to confirm/contradict
    t_neg: highest score whose sensitivity is >= 0.95 -> safe to call absent
    Youden is deliberately not used: at 3 % prevalence it produces flags that are
    almost always false positives.
    """
    if len(set(y_true)) < 2:
        return {}
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    spec = 1.0 - fpr

    # thresholds descend, spec descends, tpr ascends.
    high = [i for i in range(len(thresholds)) if spec[i] >= 0.95 and np.isfinite(thresholds[i])]
    low = [i for i in range(len(thresholds)) if tpr[i] >= 0.95 and np.isfinite(thresholds[i])]
    t_pos = float(thresholds[high[-1]]) if high else 1.0
    t_neg = float(thresholds[low[0]]) if low else 0.0

    def at(threshold: float) -> tuple[float, float, float]:
        tp = sum(1 for yy, pp in zip(y_true, scores) if yy == 1 and pp >= threshold)
        fn = sum(1 for yy, pp in zip(y_true, scores) if yy == 1 and pp < threshold)
        fp = sum(1 for yy, pp in zip(y_true, scores) if yy == 0 and pp >= threshold)
        tn = sum(1 for yy, pp in zip(y_true, scores) if yy == 0 and pp < threshold)
        sens = tp / (tp + fn) if tp + fn else 0.0
        spec_ = tn / (tn + fp) if tn + fp else 0.0
        ppv = tp / (tp + fp) if tp + fp else 0.0
        return round(sens, 3), round(spec_, 3), round(ppv, 3)

    sens_pos, spec_pos, ppv_pos = at(t_pos)
    return {
        "thr_pos": round(t_pos, 3),
        "thr_neg": round(t_neg, 3),
        "sens_at_pos": sens_pos,
        "spec_at_pos": spec_pos,
        "ppv_at_pos": ppv_pos,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--weights", default=config.DENSENET_WEIGHTS,
                        help="TorchXRayVision weight set, e.g. densenet121-res224-chex")
    parser.add_argument("--out", default="", help="calibration output path")
    parser.add_argument("--min-symmetry", type=float, default=-1.0,
                        help="drop images whose mirror correlation is below this (lateral filter)")
    parser.add_argument("--dump-probs", default="",
                        help="write raw probabilities so thresholds can be recomputed offline")
    args = parser.parse_args()

    config.DENSENET_WEIGHTS = args.weights
    out_path = pathlib.Path(args.out) if args.out else config.CALIBRATION_PATH

    records = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        records = records[: args.limit]
    if args.min_symmetry > -1:
        kept = []
        for record in records:
            if symmetry(DATA / record["file"]) >= args.min_symmetry:
                kept.append(record)
        print(f"symmetry filter >= {args.min_symmetry}: {len(kept)}/{len(records)} kept", flush=True)
        records = kept

    wanted = set(classifier.XRV_TO_CHEXBERT.values())
    per_label: dict[str, dict[str, list]] = defaultdict(lambda: {"y": [], "p": []})
    dump: dict[str, dict] = {}

    for index, record in enumerate(records, 1):
        labels = reference_labels(record["findings"], wanted)
        probs = classifier.predict(str(DATA / record["file"]))
        dump[record["id"]] = {"labels": labels, "probs": probs}
        for label, prob in probs.items():
            if label not in labels:
                continue
            per_label[label]["y"].append(labels[label])
            per_label[label]["p"].append(prob)
        if index % 50 == 0:
            print(f"  {index}/{len(records)}", flush=True)

    if args.dump_probs:
        pathlib.Path(args.dump_probs).write_text(json.dumps(dump), encoding="utf-8")
        print(f"probs -> {args.dump_probs}")

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
        points = operating_points(y, p)
        summary[label] = {
            "n": len(y),
            "positives": positives,
            "auc": round(auc, 3),
            "prevalence": round(positives / len(y), 3),
            "trusted": auc >= 0.80,
            **points,
            # kept for backwards compatibility with older calibration files
            "threshold": points.get("thr_pos", config.POSITIVE_THRESHOLD),
            "sens": points.get("sens_at_pos"),
            "spec": points.get("spec_at_pos"),
            "ppv": points.get("ppv_at_pos"),
        }

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": db.now(),
        "n_studies": len(records),
        "corpus": "openi500",
        "weights": args.weights,
        "classifier": summary,
        "confidence": {"knots": []},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = [
        "| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, s in summary.items():
        if s["auc"] is None:
            rows.append(f"| {label} | {s['positives']}/{s['n']} | â€” | {s['threshold']} | â€” | â€” | â€” | no |")
        else:
            rows.append(
                f"| {label} | {s['positives']}/{s['n']} | {s['auc']:.3f} | {s['threshold']:.2f} | "
                f"{s['sens']:.2f} | {s['spec']:.2f} | {s['ppv']:.2f} | "
                f"{'yes' if s['trusted'] else 'no'} |"
            )

    trusted = [label for label, s in summary.items() if s.get("trusted")]
    header = [
        "# Verifier gate â€” DenseNet-121 vs CheXbert on the reference report",
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
    print(f"wrote {out_path} and {OUT_MD}")


if __name__ == "__main__":
    main()
