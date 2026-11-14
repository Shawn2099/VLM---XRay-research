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

# minimum per-finding AUC for a label to be assessed at all (guardrail G2)
MIN_AUC = 0.75
MIN_PPV = 0.25               # a flag that is nearly always wrong is worse than no flag
ADVISORY_AUC = 0.65          # flag-only tier: may raise suspicion, may never clear
ADVISORY_PPV = 0.20
ADVISORY_LOW = 0.10
ADVISORY_HIGH = 0.90


def _calibration() -> dict:
    try:
        return json.loads(config.CALIBRATION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def gate() -> tuple[set[str], set[str]]:
    """(full, advisory) label sets from the measured gate.

    full     - AUC >= 0.75: may say supported or unsupported
    advisory - 0.65 <= AUC < 0.75: may only flag extreme disagreement
    everything else is not assessable.
    """
    saved = _calibration().get("classifier", {})
    if not saved:
        return set(VERIFIABLE), set()
    full: set[str] = set()
    advisory: set[str] = set()
    for label, stats in saved.items():
        if label not in VERIFIABLE:
            continue
        auc = stats.get("auc") or 0.0
        ppv = stats.get("ppv_at_pos")
        ppv = 1.0 if ppv is None else float(ppv)
        if auc >= MIN_AUC and ppv >= MIN_PPV:
            full.add(label)
        elif auc >= ADVISORY_AUC and ppv >= ADVISORY_PPV:
            advisory.add(label)
    if not full and not advisory:
        return set(VERIFIABLE), set()
    return full, advisory


def trusted() -> set[str]:
    """Backwards-compatible alias for the fully verified set."""
    return gate()[0]


def thresholds() -> dict[str, dict]:
    """Per-finding operating points from the measured gate (guardrail G3)."""
    saved = _calibration().get("classifier", {})
    return {label: stats for label, stats in saved.items() if label in VERIFIABLE}


def _cut(label: str, table: dict[str, dict]) -> tuple[float, float]:
    stats = table.get(label, {})
    return (
        float(stats.get("thr_pos", config.POSITIVE_THRESHOLD)),
        float(stats.get("thr_neg", config.UNCERTAIN_FLOOR)),
    )


def apply(
    findings: list[dict], probs: dict[str, float], include_omissions: bool = True
) -> list[dict]:
    table = thresholds()
    allowed, advisory = gate()
    rows: list[dict] = []
    mentioned: set[str] = set()

    for item in findings:
        label = item["label"]
        polarity = item["polarity"]
        mentioned.add(label)
        severity = SEVERITY.get(label, 1)
        prob = probs.get(label)

        if prob is None or (label not in allowed and label not in advisory):
            verdict = "not_assessable"
            reason = (
                "no independent image model covers this finding"
                if label not in VERIFIABLE
                else "image model does not separate this finding reliably (AUC gate)"
            )
        elif label in advisory:
            # flag-only tier: extreme disagreement may raise suspicion, agreement proves nothing
            if polarity > 0 and prob <= ADVISORY_LOW:
                verdict = "unsupported"
                reason = f"advisory: image {prob:.2f} \u2264 {ADVISORY_LOW:.2f} while report says present"
            elif polarity < 0 and prob >= ADVISORY_HIGH:
                verdict = "contradiction"
                reason = f"advisory: image {prob:.2f} \u2265 {ADVISORY_HIGH:.2f} while report says absent"
            else:
                verdict = "not_assessable"
                reason = "advisory only (weak AUC); cannot confirm or clear this finding"
        elif item.get("hedged"):
            verdict = "uncertain"
            reason = f"report hedges this finding; image {prob:.2f}"
        else:
            t_pos, t_neg = _cut(label, table) if label in table else (
                config.POSITIVE_THRESHOLD,
                config.UNCERTAIN_FLOOR,
            )
            if polarity > 0:
                if prob >= t_pos:
                    verdict, reason = "supported", f"report says present; image {prob:.2f} \u2265 {t_pos:.2f}"
                elif prob <= t_neg:
                    verdict, reason = "unsupported", f"report says present; image {prob:.2f} \u2264 {t_neg:.2f}"
                else:
                    verdict, reason = "uncertain", f"report says present; image {prob:.2f} is between {t_neg:.2f} and {t_pos:.2f}"
            else:
                if prob >= t_pos:
                    verdict, reason = "contradiction", f"report says absent; image {prob:.2f} \u2265 {t_pos:.2f}"
                else:
                    verdict, reason = "supported", f"report says absent; image {prob:.2f} < {t_pos:.2f}"

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
        for label in sorted(allowed):
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
