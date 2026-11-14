"""Does the verifier actually catch errors?

AUC against report-derived labels is biased: terse OpenI reports omit real
findings, so a correct image model is scored as a false positive. The question
that matters is relative: **is a report finding more often wrong when the
verifier flags it than when it agrees?**

Joins existing generated reports with DenseNet probabilities on the same images.

    python -m trustmed.eval.verifier_value --results test/results/medgemma500_t0/results.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict

from trustmed import config
from trustmed.services import classifier, findings, verdict

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "test" / "data" / "openi500"


def positive(labels: dict[str, int], label: str) -> bool:
    return labels.get(label, 0) == 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default="")
    parser.add_argument("--ignore-gate", action="store_true",
                        help="assess every mapped label, to measure the signal itself")
    args = parser.parse_args()

    if args.ignore_gate:
        verdict.gate = lambda: (set(verdict.VERIFIABLE), set())  # type: ignore[assignment]

    rows = [
        json.loads(line)
        for line in pathlib.Path(args.results).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if r.get("status") == 200 and r.get("report")]
    if args.limit:
        rows = rows[: args.limit]

    buckets: dict[str, Counter] = defaultdict(Counter)
    per_label: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    for index, row in enumerate(rows, 1):
        image = DATA / f"{row['id']}.png"
        if not image.is_file():
            image = DATA / f"{row['id']}.jpg"
        if not image.is_file():
            continue

        reference = row["findings"]
        generated = row["report"]
        probs = classifier.predict(str(image))

        ref_vector = findings._label_vector(reference)
        pred_vector = findings._label_vector(generated)
        ref_labels = {
            label: (1 if ref_vector[i] not in ("", None) and int(ref_vector[i]) > 0 else 0)
            for i, label in enumerate(findings.CHEXBERT_LABELS)
        }
        pred_labels = {
            label: (1 if pred_vector[i] not in ("", None) and int(pred_vector[i]) > 0 else 0)
            for i, label in enumerate(findings.CHEXBERT_LABELS)
        }

        extracted = findings.extract(generated)
        verdicts = verdict.apply(extracted, probs, include_omissions=False)

        for row_v in verdicts:
            label = row_v["label"]
            if label not in classifier.XRV_TO_CHEXBERT.values():
                continue
            if row_v["verdict"] == "not_assessable":
                continue
            # is the *report* wrong about this label, whatever the verifier said?
            wrong = positive(pred_labels, label) != positive(ref_labels, label)
            buckets[row_v["verdict"]]["rows"] += 1
            buckets[row_v["verdict"]]["wrong"] += int(wrong)
            per_label[label][row_v["verdict"]]["rows"] += 1
            per_label[label][row_v["verdict"]]["wrong"] += int(wrong)

        if index % 50 == 0:
            print(f"  {index}/{len(rows)}", flush=True)

    def rate(counter: Counter, key: str) -> float:
        return counter[key] / counter["rows"] if counter["rows"] else float("nan")

    order = ["supported", "uncertain", "unsupported", "contradiction"]
    print(f"\n{len(rows)} reports\n")
    print("| verdict | rows | report wrong | rate |")
    print("|---|---|---|---|")
    for name in order:
        counter = buckets.get(name)
        if not counter or not counter["rows"]:
            continue
        print(f"| {name} | {counter['rows']} | {counter['wrong']} | {rate(counter, 'wrong'):.3f} |")

    supported = buckets.get("supported", Counter())
    flagged = Counter()
    for name in order[1:]:
        flagged.update(buckets.get(name, Counter()))
    print(
        f"\nauto-accept (supported only): {supported['rows']} rows, "
        f"error {rate(supported, 'wrong'):.3f}"
    )
    print(
        f"flagged (everything else):    {flagged['rows']} rows, "
        f"error {rate(flagged, 'wrong'):.3f}"
    )

    out = pathlib.Path(args.out) if args.out else pathlib.Path(args.results).with_name(
        "verifier_value.json"
    )
    out.write_text(
        json.dumps(
            {
                "results": args.results,
                "n_reports": len(rows),
                "buckets": {k: dict(v) for k, v in buckets.items()},
                "per_label": {k: {kk: dict(vv) for kk, vv in v.items()} for k, v in per_label.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
