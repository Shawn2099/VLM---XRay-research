"""Model-disagreement / selective-prediction analysis.

Compares two results.jsonl files (same study IDs, e.g. CXR-LLaVA and MedGemma)
on the common CXR findings. For each finding it reports agreement, who is
correct when they disagree, and whether disagreement is a useful deferral
signal (risk–coverage).

Usage:
  python test/disagreement.py \
      test/results/report_t0/results.jsonl \
      test/results/medgemma_t0/results.jsonl
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from evaluate_api import LABELS, mentions  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def wilson(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    z = 1.96
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (round(max(0.0, centre - margin), 3), round(min(1.0, centre + margin), 3))


def load(path: str) -> dict[str, dict]:
    rows = [
        json.loads(line)
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {row["id"]: row for row in rows if row.get("status") == 200 and row.get("report")}


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    left_name = pathlib.Path(sys.argv[1]).parent.name
    right_name = pathlib.Path(sys.argv[2]).parent.name
    left = load(sys.argv[1])
    right = load(sys.argv[2])
    ids = sorted(set(left) & set(right))
    if not ids:
        raise SystemExit("no common successful IDs")

    per_label = {}
    for label, pattern in LABELS.items():
        both_pos = both_neg = left_only = right_only = 0
        left_correct = right_correct = neither = 0
        for study_id in ids:
            ref = mentions(left[study_id]["findings"], pattern)
            a = mentions(left[study_id]["report"], pattern)
            b = mentions(right[study_id]["report"], pattern)
            if a and b:
                both_pos += 1
            elif not a and not b:
                both_neg += 1
            elif a and not b:
                left_only += 1
            else:
                right_only += 1
            if a != b:
                if a == ref and b != ref:
                    left_correct += 1
                elif b == ref and a != ref:
                    right_correct += 1
                else:
                    neither += 1
        disagreements = left_only + right_only
        per_label[label] = {
            "n": len(ids),
            "both_positive": both_pos,
            "both_negative": both_neg,
            "left_only": left_only,
            "right_only": right_only,
            "disagreements": disagreements,
            "disagreement_rate": round(disagreements / len(ids), 3),
            "left_correct_when_disagreed": left_correct,
            "right_correct_when_disagreed": right_correct,
            "neither_correct_when_disagreed": neither,
        }

    # Finding-level errors grouped by whether the two models agreed.
    agree_errors = agree_total = 0
    disagree_total = 0
    disagree_left_correct = disagree_right_correct = disagree_neither = 0
    disagree_left_errors = disagree_right_errors = 0
    left_errors_total = right_errors_total = 0
    for label, pattern in LABELS.items():
        for study_id in ids:
            ref = mentions(left[study_id]["findings"], pattern)
            a = mentions(left[study_id]["report"], pattern)
            b = mentions(right[study_id]["report"], pattern)
            left_errors_total += int(a != ref)
            right_errors_total += int(b != ref)
            if a == b:
                agree_total += 1
                agree_errors += int(a != ref)
            else:
                disagree_total += 1
                disagree_left_errors += int(a != ref)
                disagree_right_errors += int(b != ref)
                if a == ref and b != ref:
                    disagree_left_correct += 1
                elif b == ref and a != ref:
                    disagree_right_correct += 1
                else:
                    disagree_neither += 1

    coverage = agree_total / (agree_total + disagree_total)
    summary = {
        "left": left_name,
        "right": right_name,
        "n_studies": len(ids),
        "finding_rows": agree_total + disagree_total,
        "agreement_rows": agree_total,
        "disagreement_rows": disagree_total,
        "coverage_if_defer_on_disagreement": round(coverage, 3),
        # Both models make the same prediction on agreement rows, so they have
        # the same error there.
        "error_rate_when_agree": round(agree_errors / max(1, agree_total), 3),
        "error_rate_agree_ci": wilson(agree_errors, agree_total),
        "left_error_rate_overall": round(left_errors_total / (agree_total + disagree_total), 3),
        "right_error_rate_overall": round(right_errors_total / (agree_total + disagree_total), 3),
        "left_error_rate_when_disagree": round(disagree_left_errors / max(1, disagree_total), 3),
        "right_error_rate_when_disagree": round(disagree_right_errors / max(1, disagree_total), 3),
        "disagreement_left_correct": disagree_left_correct,
        "disagreement_right_correct": disagree_right_correct,
        "disagreement_neither_correct": disagree_neither,
        "labels": per_label,
    }
    out = pathlib.Path("test/results/disagreement.json")
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        f"# Model disagreement — {left_name} vs {right_name}",
        "",
        f"* studies: {len(ids)}",
        f"* finding-level rows: {agree_total + disagree_total}",
        f"* models agree: {agree_total} rows ({coverage:.1%}) · "
        f"both-wrong rate **{summary['error_rate_when_agree']:.1%}** "
        f"(95% CI {summary['error_rate_agree_ci']})",
        f"* models disagree: {disagree_total} rows · left correct "
        f"{disagree_left_correct}, right correct {disagree_right_correct}, "
        f"neither {disagree_neither}",
        f"* overall finding error: left **{summary['left_error_rate_overall']:.1%}**, "
        f"right **{summary['right_error_rate_overall']:.1%}**",
        f"* if every disagreement is deferred: coverage {coverage:.1%}, "
        f"retained (agreed) error {summary['error_rate_when_agree']:.1%}; "
        f"no-deferral error left {summary['left_error_rate_overall']:.1%} / "
        f"right {summary['right_error_rate_overall']:.1%}",
        "",
        "| finding | both+ | both- | left only | right only | left correct | right correct | neither |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, data in per_label.items():
        lines.append(
            f"| {label} | {data['both_positive']} | {data['both_negative']} | "
            f"{data['left_only']} | {data['right_only']} | "
            f"{data['left_correct_when_disagreed']} | "
            f"{data['right_correct_when_disagreed']} | "
            f"{data['neither_correct_when_disagreed']} |"
        )
    pathlib.Path("test/results/disagreement.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    print(f"\nwrote {out} and test/results/disagreement.md")


if __name__ == "__main__":
    main()
