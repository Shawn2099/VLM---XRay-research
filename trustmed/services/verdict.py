"""Verdict engine: joins what the report claims with what the image shows.

Pure rules, no learning. Every row carries a human-readable reason so the UI can
answer "why is this flagged?" without a second model.
"""

from __future__ import annotations

import json

from .. import config
from . import classifier

SEVERITY = {
    "Pneumothorax": 3,
    "Pleural Effusion": 3,
    "Consolidation": 3,
    "Pneumonia": 3,
    "Fracture": 3,
    "Support Devices": 2,
    "Cardiomegaly": 2,
    "Edema": 2,
    "Lung Lesion": 2,
    "Atelectasis": 1,
    "Lung Opacity": 1,
    "Enlarged Cardiomediastinum": 1,
    "Pleural Other": 1,
    "No Finding": 0,
}

VERIFIABLE = set(classifier.XRV_TO_CHEXBERT.values()) - classifier.NOT_ASSESSABLE


def _calibration() -> dict:
    try:
        return json.loads(config.CALIBRATION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def thresholds() -> dict[str, float]:
    """Per-finding positive threshold (guardrail G3); falls back to the global one."""
    saved = _calibration().get("classifier", {})
    return {
        label: float(saved.get(label, {}).get("threshold", config.POSITIVE_THRESHOLD))
        for label in VERIFIABLE
    }


def _cut(label: str, table: dict[str, float]) -> float:
    return table.get(label, config.POSITIVE_THRESHOLD)


def apply(
    findings: list[dict], probs: dict[str, float], include_omissions: bool = True
) -> list[dict]:
    table = thresholds()
    rows: list[dict] = []
    mentioned: set[str] = set()

    for item in findings:
        label = item["label"]
        polarity = item["polarity"]
        mentioned.add(label)
        severity = SEVERITY.get(label, 1)
        prob = probs.get(label)

        if label not in VERIFIABLE or prob is None:
            verdict = "not_assessable"
            reason = "no independent image model covers this finding"
        elif item.get("hedged"):
            verdict = "uncertain"
            reason = f"report hedges this finding; image {prob:.2f}"
        else:
            cut = _cut(label, table)
            if polarity > 0:
                if prob >= cut:
                    verdict, reason = "supported", f"report says present; image {prob:.2f} \u2265 {cut:.2f}"
                elif prob >= config.UNCERTAIN_FLOOR:
                    verdict, reason = "uncertain", f"report says present; image {prob:.2f} is borderline"
                else:
                    verdict, reason = "unsupported", f"report says present; image {prob:.2f} < {config.UNCERTAIN_FLOOR:.2f}"
            else:
                if prob >= cut:
                    verdict, reason = "contradiction", f"report says absent; image {prob:.2f} \u2265 {cut:.2f}"
                else:
                    verdict, reason = "supported", f"report says absent; image {prob:.2f} agrees"

        rows.append(
            {
                **item,
                "severity": severity,
                "image_prob": prob,
                "verdict": verdict,
                "reason": ("label corrected (negated in report); " if item.get("corrected") else "")
                + reason,
            }
        )

    # Omission: image positive, report silent (guardrail G4: p >= 0.90 and PPV >= 0.5)
    if include_omissions:
        ppv = _calibration().get("classifier", {})
        for label in sorted(VERIFIABLE):
            if label in mentioned:
                continue
            prob = probs.get(label)
            if prob is None or prob < config.OMISSION_THRESHOLD:
                continue
            stats = ppv.get(label, {})
            if stats.get("ppv") is not None and float(stats["ppv"]) < config.OMISSION_MIN_PPV:
                continue
            rows.append(
                {
                    "label": label,
                    "polarity": 0,
                    "severity": SEVERITY.get(label, 1),
                    "sentence": "",
                    "span_start": -1,
                    "span_end": -1,
                    "image_prob": prob,
                    "verdict": "omission",
                    "reason": f"image suggests {label.lower()} ({prob:.2f}); report does not mention it",
                }
            )
    return rows
