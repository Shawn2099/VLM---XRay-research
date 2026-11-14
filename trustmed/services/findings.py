"""CheXbert: turns report text into 14 labels and points each one at its sentence.

CheXbert never sees the image. Four states are preserved (guardrail G5):
+1 positive, -1 negative, 0 not mentioned.
"""

from __future__ import annotations

import re
import threading

from .. import config

# model output order — do not reorder (verified against f1chexbert 0.0.2)
CHEXBERT_LABELS = [
    "Enlarged Cardiomediastinum",
    "Cardiomegaly",
    "Lung Opacity",
    "Lung Lesion",
    "Edema",
    "Consolidation",
    "Pneumonia",
    "Atelectasis",
    "Pneumothorax",
    "Pleural Effusion",
    "Pleural Other",
    "Fracture",
    "Support Devices",
    "No Finding",
]

LEXICON = {
    "Enlarged Cardiomediastinum": r"cardiomediastin|mediastinal (?:contour|width)|widened mediastinum",
    "Cardiomegaly": r"cardiomegal|enlarged (?:cardiac|heart)|heart size|cardiac silhouette",
    "Lung Opacity": r"opacit|airspace disease|infiltrat",
    "Lung Lesion": r"nodule|mass|lesion",
    "Edema": r"edema|pulmonary vascular congestion|vascular congestion",
    "Consolidation": r"consolidat",
    "Pneumonia": r"pneumonia|infectious process",
    "Atelectasis": r"atelecta",
    "Pneumothorax": r"pneumothorax|visceral pleural line",
    "Pleural Effusion": r"effusion",
    "Pleural Other": r"pleural (?:thickening|plaque)",
    "Fracture": r"fractur",
    "Support Devices": r"catheter|pacemaker|line |tube|device|stent|clip",
    "No Finding": r"no acute|normal|unremarkable|no (?:focal|significant)",
}

_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            from f1chexbert import F1CheXbert

            _model = F1CheXbert(device=config.CHEXBERT_DEVICE)
    return _model


def split_sentences(text: str) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    cursor = 0
    for line in text.splitlines():
        line_start = cursor
        cursor += len(line) + 1
        if not line.strip():
            continue
        for match in re.finditer(r"[^.!?]+[.!?]?", line):
            sentence = match.group(0).strip()
            if not sentence:
                continue
            start = line_start + match.start()
            out.append((sentence, start, start + len(sentence)))
    return out


def _label_vector(text: str) -> list:
    model = _load()
    with _lock:
        return model.get_label(text, mode="classification")


_SENTENCE_CACHE: dict[str, list] = {}

NEG_CUE = re.compile(
    r"\b(no|not|without|absence of|free of|negative for|neither|nor)\b", re.IGNORECASE
)
CONTRAST = re.compile(r"\b(but|however|except|although|though|whereas)\b", re.IGNORECASE)


def _sentence_vector(sentence: str) -> list:
    key = sentence[:300]
    if key not in _SENTENCE_CACHE:
        _SENTENCE_CACHE[key] = _label_vector(sentence)
    return _SENTENCE_CACHE[key]


def _mention_negated(sentence: str, pattern: re.Pattern) -> bool:
    """True when the label term sits behind a negation cue in this sentence."""
    if CONTRAST.search(sentence):
        return False                      # 'no X, however Y' - do not flip
    match = pattern.search(sentence)
    if match is None:
        return False
    return bool(NEG_CUE.search(sentence[: match.start()]))


def _agree(local_value, polarity: int) -> bool:
    """Does a sentence's own CheXbert label match the report-level polarity?"""
    if local_value in ("", None):
        return False
    value = int(local_value)
    return value != 0 if polarity > 0 else value == 0


def extract(text: str) -> list[dict]:
    """Return one row per *mentioned* finding.

    CheXbert classification states are preserved (guardrail G5):
      raw 1  -> polarity +1  (present)
      raw 0  -> polarity -1  (explicitly absent)
      raw -1 -> polarity +1, hedged=True  ("cannot exclude ...")
      raw '' -> not mentioned, and therefore not returned at all.

    Two guardrails on top (G9):
      * a positive label every one of whose mentions is negated is flipped to negative
        (CheXbert mislabels list negations: "no consolidation, atelectasis, or pneumothorax");
      * the quoted sentence must itself be labelled the same way, otherwise no quote.
    """
    vector = _label_vector(text)
    sentences = split_sentences(text)

    findings: list[dict] = []
    for index, label in enumerate(CHEXBERT_LABELS):
        raw = vector[index] if index < len(vector) else ""
        if raw in ("", None):
            continue                      # not mentioned is not "absent"

        value = int(raw)
        hedged = value == -1
        polarity = -1 if value == 0 else 1

        pattern = re.compile(LEXICON.get(label, ""), re.IGNORECASE)
        candidates = [s for s in sentences if pattern.search(s[0])]

        corrected = False
        if polarity > 0 and not hedged and candidates and all(
            _mention_negated(s[0], pattern) for s in candidates
        ):
            polarity = -1                 # negation guard
            corrected = True

        quote = ("", -1, -1)
        if label != "No Finding":         # report-level label, not a sentence
            for sentence, start, end in candidates:
                local = _sentence_vector(sentence)
                if index < len(local) and _agree(local[index], polarity):
                    quote = (sentence, start, end)
                    break
            if not quote[0] and candidates:
                for sentence, start, end in candidates:
                    if _mention_negated(sentence, pattern) == (polarity < 0):
                        quote = (sentence, start, end)
                        break

        findings.append(
            {
                "label": label,
                "polarity": polarity,
                "hedged": hedged,
                "sentence": quote[0],
                "span_start": quote[1],
                "span_end": quote[2],
                "corrected": corrected,
            }
        )
    return findings


def self_test() -> dict:
    """Guardrail G1/G5/G9: label order, four states, negation correction."""
    text = "The heart is enlarged. There is a small left pleural effusion. No pneumothorax."
    rows = {row["label"]: row for row in extract(text)}
    checks = {
        "Cardiomegaly positive": rows.get("Cardiomegaly", {}).get("polarity") == 1,
        "Pleural Effusion positive": rows.get("Pleural Effusion", {}).get("polarity") == 1,
        "Pneumothorax negative": rows.get("Pneumothorax", {}).get("polarity") == -1,
        "Atelectasis not mentioned": "Atelectasis" not in rows,
    }
    negation = {
        row["label"]: row
        for row in extract("No focal consolidation, atelectasis, or pneumothorax is identified.")
    }
    checks["list negation corrected"] = all(
        negation.get(label, {}).get("polarity") == -1
        for label in ("Atelectasis", "Pneumothorax")
    )
    return {"ok": all(checks.values()), "checks": checks}
