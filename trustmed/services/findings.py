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


def extract(text: str) -> list[dict]:
    """Return [{label, polarity, sentence, span_start, span_end, corrected}] for mentioned labels.

    Two guardrails on top of raw CheXbert (G9):
      * a positive label every one of whose mentions is negated is flipped to negative
        (CheXbert mislabels list negations, e.g. "no consolidation, atelectasis, or
        pneumothorax");
      * the quoted sentence must be one whose own labels agree with the report label,
        otherwise no quote is shown rather than a contradictory one.
    """
    vector = _label_vector(text)
    sentences = split_sentences(text)

    findings: list[dict] = []
    for index, label in enumerate(CHEXBERT_LABELS):
        raw = vector[index] if index < len(vector) else ""
        polarity = 0 if raw in ("", None) else int(raw)
        if polarity == 0:
            continue                      # not mentioned: G5, not "absent"

        pattern = re.compile(LEXICON.get(label, ""), re.IGNORECASE)
        candidates = [s for s in sentences if pattern.search(s[0])]

        corrected = False
        if polarity > 0 and candidates and all(_mention_negated(s[0], pattern) for s in candidates):
            polarity = -1                 # negation guard
            corrected = True

        quote = ("", -1, -1)
        for sentence, start, end in candidates:
            local = _sentence_vector(sentence)
            if index < len(local) and local[index] not in ("", None) and int(local[index]) == polarity:
                quote = (sentence, start, end)
                break
        if not quote[0] and candidates:
            # no sentence agrees: show the first non-contradictory one, or nothing
            for sentence, start, end in candidates:
                if _mention_negated(sentence, pattern) == (polarity < 0):
                    quote = (sentence, start, end)
                    break

        findings.append(
            {
                "label": label,
                "polarity": polarity,
                "sentence": quote[0],
                "span_start": quote[1],
                "span_end": quote[2],
                "corrected": corrected,
            }
        )
    return findings


def self_test() -> dict:
    """Guardrail G1: label order and polarity on a fixture report."""
    text = "The heart is enlarged. There is a small left pleural effusion. No pneumothorax."
    rows = {row["label"]: row["polarity"] for row in extract(text)}
    checks = {
        "Cardiomegaly": rows.get("Cardiomegaly") == 1,
        "Pleural Effusion": rows.get("Pleural Effusion") == 1,
        "Pneumothorax": rows.get("Pneumothorax") == -1,
        "Atelectasis": rows.get("Atelectasis") in (None, 0),
    }
    return {"ok": all(checks.values()), "checks": checks, "rows": rows}
