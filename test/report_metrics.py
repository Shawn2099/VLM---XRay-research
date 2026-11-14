"""Clinical + text metrics for generated CXR reports.

Metrics:
  * CheXbert 14-label micro/macro F1 (Stanford checkpoint, rrg binarisation)
  * RadGraph F1 (RG_E, RG_ER, RG_Complete; model_type="radgraph")
  * BLEU-4 (sacrebleu corpus BLEU)
  * ROUGE-L (rouge-score)
  * BERTScore (distilbert-base-uncased, optional)

Run in the pinned `metrics-venv`:
  metrics-venv\\Scripts\\python test\\report_metrics.py \
      test/results/medgemma500_t0/results.jsonl --out test/results/medgemma500_metrics.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time

CHEXBERT_LABELS = [
    "Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity", "Lung Lesion",
    "Edema", "Consolidation", "Pneumonia", "Atelectasis", "Pneumothorax",
    "Pleural Effusion", "Pleural Other", "Fracture", "Support Devices",
    "No Finding",
]


def normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--out", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-bertscore", action="store_true")
    parser.add_argument("--skip-radgraph", action="store_true")
    parser.add_argument("--skip-chexbert", action="store_true")
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in pathlib.Path(args.results).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if row.get("status") == 200 and row.get("report")]
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("no successful reports")
    hyps = [normalize(row["report"]) for row in rows]
    refs = [normalize(row["findings"]) for row in rows]
    print(f"{len(rows)} reports from {args.results}", flush=True)

    result = {"results": args.results, "n": len(rows)}

    # --- text metrics -----------------------------------------------------
    import sacrebleu
    from rouge_score import rouge_scorer

    result["bleu4"] = round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    result["rougeL"] = round(
        statistics.mean(
            scorer.score(ref, hyp)["rougeL"].fmeasure for ref, hyp in zip(refs, hyps)
        ),
        4,
    )
    print("text metrics done", flush=True)

    # --- CheXbert ----------------------------------------------------------
    if not args.skip_chexbert:
        print("loading CheXbert...", flush=True)
        started = time.time()
        from f1chexbert import F1CheXbert

        chexbert = F1CheXbert(device="cpu")
        hyp_labels = [chexbert.get_label(text, mode="rrg") for text in hyps]
        ref_labels = [chexbert.get_label(text, mode="rrg") for text in refs]
        print(f"CheXbert done in {time.time() - started:.1f}s", flush=True)

        label_stats = {}
        tp_total = fp_total = fn_total = tn_total = 0
        for index, label in enumerate(CHEXBERT_LABELS):
            tp = fp = fn = tn = 0
            for ref, hyp in zip(ref_labels, hyp_labels):
                r = int(ref[index]) if index < len(ref) else 0
                h = int(hyp[index]) if index < len(hyp) else 0
                if r and h:
                    tp += 1
                elif h:
                    fp += 1
                elif r:
                    fn += 1
                else:
                    tn += 1
            tp_total += tp
            fp_total += fp
            fn_total += fn
            tn_total += tn
            label_stats[label] = {
                "reference_positive": tp + fn,
                "predicted_positive": tp + fp,
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "f1": round(f1(tp, fp, fn), 3),
            }
        result["chexbert"] = {
            "micro_f1": round(f1(tp_total, fp_total, fn_total), 4),
            "macro_f1": round(statistics.mean(v["f1"] for v in label_stats.values()), 4),
            "omission_rate": round(fn_total / max(1, tp_total + fn_total), 4),
            "hallucination_rate": round(fp_total / max(1, fp_total + tn_total), 4),
            "labels": label_stats,
        }

    # --- RadGraph ----------------------------------------------------------
    if not args.skip_radgraph:
        print("loading RadGraph...", flush=True)
        started = time.time()
        from radgraph import F1RadGraph

        radgraph = F1RadGraph(reward_level="all", model_type="radgraph")
        mean_reward, _, _, _ = radgraph(refs=refs, hyps=hyps)
        result["radgraph"] = {
            "RG_E": round(float(mean_reward[0]), 4),
            "RG_ER": round(float(mean_reward[1]), 4),
            "RG_Complete": round(float(mean_reward[2]), 4),
            "model_type": "radgraph",
        }
        print(f"RadGraph done in {time.time() - started:.1f}s", flush=True)

    # --- BERTScore ---------------------------------------------------------
    if not args.skip_bertscore:
        print("BERTScore (distilbert)...", flush=True)
        started = time.time()
        from bert_score import score

        precision, recall, f1s = score(
            hyps, refs, model_type="distilbert-base-uncased", num_layers=5,
            batch_size=16, device="cpu", rescale_with_baseline=False,
        )
        result["bertscore"] = {
            "precision": round(float(precision.mean()), 4),
            "recall": round(float(recall.mean()), 4),
            "f1": round(float(f1s.mean()), 4),
            "model": "distilbert-base-uncased",
        }
        print(f"BERTScore done in {time.time() - started:.1f}s", flush=True)

    out = pathlib.Path(args.out) if args.out else pathlib.Path(args.results).with_name("metrics.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        f"# Report metrics — {pathlib.Path(args.results).parent.name}",
        "",
        f"* reports: {len(rows)}",
        f"* BLEU-4: {result['bleu4']}",
        f"* ROUGE-L: {result['rougeL']}",
    ]
    if "chexbert" in result:
        lines += [
            f"* CheXbert micro F1: **{result['chexbert']['micro_f1']}**",
            f"* CheXbert macro F1: **{result['chexbert']['macro_f1']}**",
            f"* CheXbert omission rate: {result['chexbert']['omission_rate']}",
            f"* CheXbert false-positive/hallucination rate: {result['chexbert']['hallucination_rate']}",
        ]
    if "radgraph" in result:
        lines += [
            f"* RadGraph RG_ER: **{result['radgraph']['RG_ER']}** "
            f"(RG_E {result['radgraph']['RG_E']}, complete {result['radgraph']['RG_Complete']})",
        ]
    if "bertscore" in result:
        lines += [f"* BERTScore F1: {result['bertscore']['f1']}"]
    lines += ["", "| CheXbert finding | ref+ | pred+ | TP | FP | FN | F1 |", "|---|---|---|---|---|---|---|"]
    if "chexbert" in result:
        for label, stats in result["chexbert"]["labels"].items():
            lines.append(
                f"| {label} | {stats['reference_positive']} | {stats['predicted_positive']} | "
                f"{stats['tp']} | {stats['fp']} | {stats['fn']} | {stats['f1']} |"
            )
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out} and {out.with_suffix('.md')}")


if __name__ == "__main__":
    main()
