"""Run a dataset through the deployed CXR-LLaVA API and score the results.

Reads test/data/openi/metadata.jsonl (see fetch_openi.py), posts every image to
/report, stores every response and computes:

  * success / empty / error rates and latency distribution
  * mention precision/recall/F1 for common CXR findings (negation-aware,
    crude keyword matching against the OpenI FINDINGS text)
  * unigram F1 between generated report and reference findings
  * repetition and length statistics
  * concrete false-positive / false-negative examples for manual review

Usage:
  python test/evaluate_api.py --api-key KEY --limit 120 --temperature 0
  python test/evaluate_api.py --api-key KEY --temperature 0.2 --out test/results/t02

The API serialises inference, so requests are sent one at a time.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "openi"
RESULTS = ROOT / "results"

STOPWORDS = {
    "the", "and", "with", "without", "there", "this", "that", "are", "was",
    "were", "for", "from", "has", "have", "had", "not", "but", "its", "his",
    "her", "their", "which", "seen", "shown", "also", "into", "over", "within",
    "normal", "otherwise", "appear", "appears", "visualized", "noted",
}

LABELS = {
    "atelectasis": r"atelecta\w*",
    "cardiomegaly": (
        r"cardiomegal\w*|"
        r"enlarged (?:cardiac|heart)|"
        r"cardiac silhouette (?:is |appears )?(?:enlarged|borderline|prominent)|"
        r"heart size (?:is |appears )?(?:enlarged|borderline)|"
        r"cardiac enlargement"
    ),
    "consolidation": r"consolidat\w*",
    "edema": r"edema|oedema",
    "effusion": r"effusion\w*",
    "pneumonia": r"pneumoni\w*|infectious process|infection",
    "pneumothorax": r"pneumothorax|pneumothoraces",
    "nodule_mass": r"nodule\w*|mass\b|masses\b",
    "fracture": r"fractur\w*",
    "normal": r"no acute (?:cardiopulmonary )?(?:abnormality|disease)|within normal limits|normal chest|unremarkable",
}

NEGATION_CUES = re.compile(
    r"\b(no|without|free of|negative for|absence of|no evidence of|"
    r"no significant|no definite|no acute)\b",
    re.I,
)


def negated(text: str, start: int, end: int) -> bool:
    """Crude negation scope: a cue before the match, not across a clause break.

    Commas do NOT end the scope: "no pneumonia, vascular congestion, or pleural
    effusion" negates all three.  A full stop/semicolon, a contrast word, or a
    new "there is/are" clause does.
    """
    before = text[max(0, start - 70) : start].lower()
    for cue in NEGATION_CUES.finditer(before):
        between = before[cue.end() :]
        if not re.search(
            r"[.;]|\b(but|however|although|though|whereas|except)\b|"
            r"\bthere (?:is|are|was|were)\b",
            between,
            re.I,
        ):
            return True
    after = text[end : end + 35].lower()
    if re.match(r"\s*(?:is|are|was|were)?\s*not\b", after):
        return True
    if re.match(r"\s*(?:has|have|is|are)\s+(?:resolved|cleared)", after):
        return True
    return False


def mentions(text: str, pattern: str) -> bool:
    for match in re.finditer(pattern, text, re.I):
        if not negated(text, match.start(), match.end()):
            return True
    return False


def tokens(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-z]+", text.lower())
        if len(word) > 2 and word not in STOPWORDS
    ]


def unigram_f1(prediction: str, reference: str) -> float:
    predicted = Counter(tokens(prediction))
    actual = Counter(tokens(reference))
    if not predicted or not actual:
        return 0.0
    overlap = sum((predicted & actual).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(predicted.values())
    recall = overlap / sum(actual.values())
    return 2 * precision * recall / (precision + recall)


def repetition_ratio(text: str, n: int = 8) -> float:
    words = re.findall(r"\S+", text.lower())
    if len(words) < n:
        return 0.0
    grams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
    return 1.0 - len(set(grams)) / len(grams)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def post_image(session, base_url, key, path, temperature, top_p, timeout):
    started = time.time()
    with path.open("rb") as handle:
        response = session.post(
            f"{base_url}/report",
            headers={"X-API-Key": key},
            files={"file": (path.name, handle, "image/jpeg")},
            data={"temperature": str(temperature), "top_p": str(top_p)},
            timeout=timeout,
        )
    elapsed = time.time() - started
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text[:500]}
    return response.status_code, payload, elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default=os.environ.get("CXR_API_KEY", ""))
    parser.add_argument("--data", default=str(DATA), help="dataset directory with metadata.jsonl")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--out", default="")
    parser.add_argument("--frontal-only", action="store_true",
                        help="keep only portrait/square images (drop likely laterals)")
    parser.add_argument("--rescore", default="",
                        help="recompute summary from an existing results.jsonl")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("pass --api-key or set CXR_API_KEY")

    data_dir = Path(args.data)
    errors = Counter()

    if args.rescore:
        results_path = Path(args.rescore)
        rows = [
            json.loads(line)
            for line in results_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        out_dir = results_path.parent
        latencies = []
        for row in rows:
            if row.get("status") == 200 and row.get("report"):
                latencies.append(float(row.get("latency_s") or 0.0))
            elif row.get("status") == 200:
                errors["empty report"] += 1
            else:
                errors[f"HTTP {row.get('status')}"] += 1
        print(f"rescored {len(rows)} rows from {results_path}")
    else:
        metadata = [
            json.loads(line)
            for line in (data_dir / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if args.limit:
            metadata = metadata[: args.limit]
        if args.frontal_only:
            from PIL import Image as PILImage

            kept = []
            for record in metadata:
                with PILImage.open(data_dir / record["file"]) as image:
                    if image.height >= image.width:
                        kept.append(record)
            metadata = kept
            print(f"frontal-only filter: {len(metadata)} images")
        if not metadata:
            raise SystemExit(f"no records in {data_dir}")

        out_dir = Path(args.out) if args.out else RESULTS / f"report_t{args.temperature:g}"
        out_dir.mkdir(parents=True, exist_ok=True)
        session = requests.Session()

        rows = []
        latencies = []

        for index, record in enumerate(metadata, 1):
            path = data_dir / record["file"]
            status, payload, elapsed = post_image(
                session,
                args.base_url,
                args.api_key,
                path,
                args.temperature,
                args.top_p,
                args.timeout,
            )
            report = (payload.get("report") or "").strip()
            row = {
                **record,
                "status": status,
                "latency_s": round(elapsed, 3),
                "report": report,
                "source": payload.get("source"),
                "error": None if status == 200 else payload.get("detail"),
            }
            if status == 200 and not report:
                errors["empty report"] += 1
            elif status != 200:
                errors[f"HTTP {status}"] += 1
            else:
                latencies.append(elapsed)
            rows.append(row)
            if index % 10 == 0 or index == len(metadata):
                print(
                    f"{index}/{len(metadata)}  ok={sum(1 for r in rows if r['status'] == 200)}  "
                    f"mean={statistics.mean(latencies):.2f}s"
                    if latencies
                    else f"{index}/{len(metadata)}",
                    flush=True,
                )

        with (out_dir / "results.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    ok_rows = [row for row in rows if row["status"] == 200 and row["report"]]
    label_stats = {}
    confusion = Counter()
    examples = {"false_positive": [], "false_negative": []}

    for label, pattern in LABELS.items():
        tp = fp = fn = tn = 0
        for row in ok_rows:
            reference = mentions(row["findings"], pattern)
            prediction = mentions(row["report"], pattern)
            if reference and prediction:
                tp += 1
            elif prediction and not reference:
                fp += 1
                if len(examples["false_positive"]) < 8:
                    examples["false_positive"].append(
                        {"id": row["id"], "label": label, "report": row["report"][:400],
                         "reference": row["findings"][:300]}
                    )
            elif reference and not prediction:
                fn += 1
                if len(examples["false_negative"]) < 8:
                    examples["false_negative"].append(
                        {"id": row["id"], "label": label, "report": row["report"][:400],
                         "reference": row["findings"][:300]}
                    )
            else:
                tn += 1
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        label_stats[label] = {
            "reference_positive": tp + fn,
            "predicted_positive": tp + fp,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }
        confusion.update({"tp": tp, "fp": fp, "fn": fn, "tn": tn})

    scores = [unigram_f1(row["report"], row["findings"]) for row in ok_rows]
    reps = [repetition_ratio(row["report"]) for row in ok_rows]
    lengths = [len(re.findall(r"\S+", row["report"])) for row in ok_rows]

    macro_f1 = statistics.mean(v["f1"] for v in label_stats.values())
    summary = {
        "dataset": f"OpenI / IU Chest X-ray (HF mirror) [{data_dir.name}]",
        "n": len(rows),
        "ok": len(ok_rows),
        "errors": dict(errors),
        "temperature": args.temperature,
        "top_p": args.top_p,
        "latency_s": {
            "mean": round(statistics.mean(latencies), 3) if latencies else 0,
            "median": round(statistics.median(latencies), 3) if latencies else 0,
            "p95": round(percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3) if latencies else 0,
        },
        "report_words": {
            "mean": round(statistics.mean(lengths), 1) if lengths else 0,
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
        },
        "repetition_8gram": {
            "mean": round(statistics.mean(reps), 4) if reps else 0,
            "max": round(max(reps), 4) if reps else 0,
        },
        "unigram_f1": round(statistics.mean(scores), 4) if scores else 0,
        "macro_f1": round(macro_f1, 4),
        "micro": {
            "precision": round(confusion["tp"] / (confusion["tp"] + confusion["fp"]), 3)
            if confusion["tp"] + confusion["fp"] else 0,
            "recall": round(confusion["tp"] / (confusion["tp"] + confusion["fn"]), 3)
            if confusion["tp"] + confusion["fn"] else 0,
        },
        "labels": label_stats,
        "examples": examples,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        f"# CXR-LLaVA evaluation — temperature {args.temperature:g}",
        "",
        f"* dataset: {summary['dataset']}",
        f"* images: {summary['n']}  ·  successful: {summary['ok']}  ·  errors: {summary['errors']}",
        f"* latency: mean {summary['latency_s']['mean']} s, median {summary['latency_s']['median']} s, "
        f"p95 {summary['latency_s']['p95']} s, max {summary['latency_s']['max']} s",
        f"* report length: {summary['report_words']['mean']} words "
        f"({summary['report_words']['min']}–{summary['report_words']['max']})",
        f"* repetition (8-gram): mean {summary['repetition_8gram']['mean']}, "
        f"max {summary['repetition_8gram']['max']}",
        f"* unigram F1 vs reference: **{summary['unigram_f1']}**",
        f"* finding macro F1: **{summary['macro_f1']}**  "
        f"(micro P {summary['micro']['precision']} / R {summary['micro']['recall']})",
        "",
        "| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, stats in label_stats.items():
        lines.append(
            f"| {label} | {stats['reference_positive']} | {stats['predicted_positive']} | "
            f"{stats['tp']} | {stats['fp']} | {stats['fn']} | {stats['precision']} | "
            f"{stats['recall']} | {stats['f1']} |"
        )
    lines += ["", "## Sample disagreements", ""]
    for kind in ("false_positive", "false_negative"):
        lines.append(f"### {kind.replace('_', ' ')}")
        for example in examples[kind][:4]:
            lines += [
                f"* **{example['id']} / {example['label']}**",
                f"  * model: {example['report'][:220]}",
                f"  * reference: {example['reference'][:220]}",
            ]
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2)[:4000])
    print(f"\nwrote {out_dir}/summary.json, summary.md, results.jsonl")


if __name__ == "__main__":
    main()
