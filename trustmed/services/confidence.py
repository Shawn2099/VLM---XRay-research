"""Report-level confidence, fitted on held-out studies when calibration exists.

Not the generator's own probability: it is derived from verdicts, so a confident
hallucination scores low. Omissions are penalised at half weight (guardrail G8
also blocks auto-accept for very short reports).
"""

from __future__ import annotations

import json

from .. import config

SUPPORT_VALUE = {
    "supported": 1.0,
    "not_assessable": None,     # excluded from the average
    "uncertain": 0.5,
    "unsupported": 0.0,
    "contradiction": 0.0,
    "omission": 0.35,           # half weight, partial credit
}
OMISSION_WEIGHT = 0.5


def _knots() -> list[list[float]]:
    try:
        data = json.loads(config.CALIBRATION_PATH.read_text(encoding="utf-8"))
        return [[float(x), float(y)] for x, y in data.get("confidence", {}).get("knots", [])]
    except Exception:
        return []


def _isotonic(value: float, knots: list[list[float]]) -> float:
    if not knots:
        return value
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x0 <= value <= x1:
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (value - x0) / (x1 - x0)
    return knots[0][1] if value < knots[0][0] else knots[-1][1]


def score(rows: list[dict]) -> float:
    total = 0.0
    weight = 0.0
    evidence = 0.0
    for row in rows:
        value = SUPPORT_VALUE.get(row["verdict"])
        if value is None:
            continue
        severity = max(1, int(row.get("severity", 1)))
        row_weight = severity * (OMISSION_WEIGHT if row["verdict"] == "omission" else 1.0)
        total += value * row_weight
        weight += row_weight
        evidence += severity

    if weight == 0:
        return 0.30     # nothing verifiable: do not pretend to be confident

    raw = total / weight
    # thin evidence must not read as certainty (a 1-finding report is not 1.0)
    coverage = min(1.0, evidence / 8.0)
    raw = 0.5 + (raw - 0.5) * coverage
    return round(max(0.0, min(1.0, _isotonic(raw, _knots()))), 3)


def status(confidence: float, rows: list[dict], threshold: float) -> str:
    verifiable = [r for r in rows if r["verdict"] != "not_assessable"]

    if any(r["verdict"] == "contradiction" and r["severity"] >= 3 for r in verifiable):
        return "review_required"
    if confidence < threshold:
        return "review_required"
    if any(r["verdict"] in {"unsupported", "contradiction", "omission"} and r["severity"] >= 2
           for r in verifiable):
        return "review_suggested"
    if len(verifiable) < config.MIN_FINDINGS_FOR_AUTO_ACCEPT:
        return "review_suggested"     # catch-all "normal" must not auto-pass
    return "auto_accepted"
