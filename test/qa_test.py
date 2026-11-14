"""Yes/no question-answering check on OpenI images.

Asks a fixed question about cardiomegaly and pleural effusion and compares the
model's yes/no answer with a negation-aware keyword label derived from the
reference FINDINGS text. Crude, but it catches polarity errors and refusals.

Run: python test/qa_test.py --api-key KEY --limit 25
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "openi"

QUESTIONS = {
    "cardiomegaly": re.compile(
        r"cardiomegal\w*|enlarged (?:cardiac|heart)|"
        r"cardiac silhouette (?:is |appears )?(?:enlarged|borderline|prominent)|"
        r"heart size (?:is |appears )?(?:enlarged|borderline)|cardiac enlargement",
        re.I,
    ),
    "effusion": re.compile(r"effusion\w*", re.I),
}

NEGATION = re.compile(
    r"\b(no|without|free of|negative for|absence of|no evidence of|"
    r"no significant|no definite|no acute)\b",
    re.I,
)


def negated(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 70) : start].lower()
    for cue in NEGATION.finditer(before):
        between = before[cue.end() :]
        if not re.search(
            r"[.;]|\b(but|however|although|though|whereas|except)\b|"
            r"\bthere (?:is|are|was|were)\b",
            between,
            re.I,
        ):
            return True
    after = text[end : end + 35].lower()
    return bool(re.match(r"\s*(?:is|are|was|were)?\s*not\b", after))


def positive(text: str, pattern: re.Pattern) -> bool:
    return any(not negated(text, m.start(), m.end()) for m in pattern.finditer(text))


def answer_polarity(answer: str):
    """Return True/False/None from a free-text yes/no answer.

    Look at the opening polarity first: MedGemma often says "Yes, there is
    cardiomegaly. There is no effusion." and a whole-string "no" search would
    wrongly call that negative.
    """
    low = (answer or "").strip().lower()
    if not low:
        return None
    opening = re.match(r"^(yes|no)\b", low)
    if opening:
        return opening.group(1) == "yes"

    head = re.split(r"\b(?:but|however|although|though)\b", low, maxsplit=1)[0]
    if re.search(
        r"\b(no|without|negative for|absence of|not seen|not present|free of)\b",
        head,
    ):
        return False
    if re.search(
        r"\b(yes|there is|there are|present|consistent with|suggest|identified)\b",
        head,
    ):
        return True
    if re.search(r"\b(normal|within normal limits|unremarkable|clear)\b", head):
        return False
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--out", default="test/results/qa.json")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key")

    metadata = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.limit]

    rows = []
    for index, record in enumerate(metadata, 1):
        for label, pattern in QUESTIONS.items():
            question = (
                "Is there cardiomegaly?" if label == "cardiomegaly"
                else "Is there a pleural effusion?"
            )
            with (DATA / record["file"]).open("rb") as handle:
                response = requests.post(
                    f"{args.base_url}/ask",
                    headers={"X-API-Key": args.api_key},
                    files={"file": (record["file"], handle, "image/jpeg")},
                    data={"question": question, "temperature": "0", "top_p": "1"},
                    timeout=300,
                )
            body = response.json()
            answer = (body.get("answer") or "").strip()
            truth = positive(record["findings"], pattern)
            predicted = answer_polarity(answer)
            rows.append(
                {
                    "id": record["id"],
                    "label": label,
                    "reference_positive": truth,
                    "answer": answer,
                    "predicted_positive": predicted,
                    "status": response.status_code,
                    "correct": predicted == truth,
                }
            )
        if index % 10 == 0:
            print(f"{index}/{len(metadata)}", flush=True)

    correct = sum(1 for row in rows if row["correct"])
    per_label = {}
    for label in QUESTIONS:
        subset = [row for row in rows if row["label"] == label]
        per_label[label] = {
            "n": len(subset),
            "accuracy": round(sum(r["correct"] for r in subset) / max(1, len(subset)), 3),
            "reference_positive": sum(1 for r in subset if r["reference_positive"]),
            "polarity_unknown": sum(1 for r in subset if r["predicted_positive"] is None),
        }
    summary = {
        "n_questions": len(rows),
        "accuracy": round(correct / max(1, len(rows)), 3),
        "per_label": per_label,
        "rows": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
