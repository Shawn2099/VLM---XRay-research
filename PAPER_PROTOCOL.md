# Paper protocol — open-weight CXR report generation

Working title: **A reproducible open-weight pipeline for chest X-ray report
generation: comparative evaluation of CXR-LLaVA and MedGemma 1.5 4B with DICOM
preprocessing and model-disagreement analysis.**

Status: pilot complete; expanded evaluation in progress (2026-11-14).

## 1. Research questions

* **RQ1 — Quality:** Under identical DICOM/8-bit preprocessing, prompts and
  hardware, how do CXR-LLaVA v1.5 and MedGemma 1.5 4B compare on report quality
  (CheXbert/RadGraph/text metrics) and finding accuracy?
* **RQ2 — Preprocessing:** How much does DICOM windowing/monochrome handling
  change report quality versus sending an already-8-bit image?
* **RQ3 — Uncertainty:** Does disagreement between the two models predict
  clinically important errors, and can it be used as a deferral signal?
* **RQ4 — Deployment:** What are the latency, VRAM and cost trade-offs on a
  single 24 GB GPU?

## 2. Contributions

1. A reproducible, open-weight CXR reporting pipeline with DICOM windowing,
   API/UI, model switching and a public test harness.
2. A head-to-head evaluation of CXR-LLaVA and MedGemma 1.5 4B using clinical
   report metrics, not only keyword overlap.
3. A disagreement/selective-prediction analysis of a conservative versus a
   sensitive model, with deployment cost measurements.

## 3. Data

| Set | Size | Use |
|---|---|---|
| OpenI full frontal subset | up to ~1,800 unique reports | primary zero-shot test set |
| OpenI benchmark subset | **500 studies** (100 MB) | main results, bootstrap CIs |
| OpenI pilot | 120 studies | pilot / regression |
| MIMIC-CXR-JPG | official test split | secondary validation, if credentialed |
| Saintgits de-identified studies | 50–100 | reader study, if ethics approved |

OpenI is public, research-use; reports are FINDINGS sections. The mirror used is
`Shrey-1329/cxiu_hf_dataset` because the NLM site was under maintenance.
No training is performed in the current study; all evaluation is zero-shot.

## 4. Models and inference

| Model | Params | Precision | Environment | VRAM |
|---|---|---|---|---|
| ECOFRI/CXR-LLAVA-v2 | 7B | bf16 | transformers 4.36.2, torch 2.5 | 13.2 GiB |
| google/medgemma-1.5-4b-it | 4.3B | bf16 | venv transformers 4.51.3, torch 2.5 | 8.0 GiB |

Prompts, seeds (temperature 0), preprocessing and API contract are frozen and
stored in the repository. MedGemma is gated under Google HAI-DEF terms.

## 5. Metrics

**Automatic report metrics**
- CheXbert 14-label micro/macro F1 (primary clinical metric; Stanford academic
  licence, non-commercial).
- RadGraph F1 (RG_ER primary; `model_type="radgraph"`, MIT code/weights).
- BLEU-4 (sacrebleu), ROUGE-L (rouge-score), BERTScore
  (`distilbert-base-uncased`).
- Hallucination/omission rate on five critical findings.
- Negation/polarity accuracy on a balanced QA set.

Pinned metric environment: torch 2.4.1+cpu, transformers 4.49.0,
`huggingface_hub<1.0`, numpy 1.26.4, radgraph 0.1.18, f1chexbert 0.0.2,
sacrebleu 2.6.0, rouge-score 0.1.2, bert-score 0.3.13.

**Reader study (if available)**
- 50–100 studies, 2 radiologists, blinded, randomized order.
- 5-point correctness, hallucination, omission, usefulness.
- Cohen's kappa; adjudication of disagreements.

**Deployment**
- Mean/median/p95 latency, VRAM, throughput, model load time.

**Statistics**
- Bootstrap 95 % CIs (1,000 resamples), paired tests for model comparison,
  Holm correction for multiple findings.

## 6. Analyses

1. Main table: 500 OpenI studies, both models, all metrics + CIs.
2. Frontal-only subset and view-stratified error analysis.
3. DICOM-windowed vs pre-8-bit ablation (100 studies).
4. Prompt ablation for MedGemma (structured vs concise).
5. Model disagreement: 2×2 agreement on 10 findings; risk–coverage curve for
   deferral; examples of complementary errors.
6. Efficiency: latency/VRAM/cost per 1,000 reports.

## 7. Paper outline

1. Introduction — deployment gap, open-weight models, DICOM reality.
2. Related work — CXR report generation, medical VLMs, evaluation.
3. Methods — pipeline, preprocessing, models, prompts, metrics, statistics.
4. Results — RQ1–RQ4 tables/figures.
5. Discussion — model choice, conservative vs sensitive, clinical safety.
6. Limitations — OpenI size/domain, zero-shot, no reader study if unavailable,
   automated metric limits, licence restrictions.
7. Reproducibility statement and artefact list.

Target venues: ML4H / MICCAI workshop / ISBI / SPIE Medical Imaging; journal
extension: Journal of Medical Imaging or IEEE JBHI.

## 8. Current pilot results (to be replaced by 500-study results)

| Metric | CXR-LLaVA | MedGemma |
|---|---|---|
| 120-image macro F1 | 0.150 | 0.228 |
| 74-frontal macro F1 | 0.096 | 0.164 |
| Unigram F1 | 0.209 | 0.275 |
| QA accuracy (100) | 0.90 | 0.71 |
| Latency | 2.01 s | 3.57 s |

Pilot conclusion: MedGemma is better on report quality, CXR-LLaVA is faster and
more conservative; neither is clinically usable. The 500-study run and
CheXbert/RadGraph metrics are the paper-grade evidence.

500-study MedGemma: keyword macro F1 0.186, unigram 0.276, CheXbert micro/macro
0.251/0.161, omission 68.5 %, false-positive 9.4 %, RadGraph RG_ER 0.293,
BLEU-4 4.49, ROUGE-L 0.216, BERTScore 0.820, latency 3.61 s.
CXR-LLaVA: macro 0.118, unigram 0.214, CheXbert 0.214/0.135, omission 71.3 %,
false-positive 11.0 %, RadGraph 0.226, BLEU 3.56, ROUGE 0.208, BERTScore 0.822,
latency 1.96 s. CheXbert micro is 0.214 vs 0.251 and RadGraph 0.226 vs 0.293 in
MedGemma's favor; BERTScore is effectively tied. Paired macro difference
+0.066 [0.010, 0.121], p = 0.012; unigram +0.062 [0.051, 0.072], p < 0.001.
The larger set is materially stricter than the 120-image pilot.

Balanced QA: CXR cardiomegaly sensitivity 0.100 / specificity 0.967, effusion
0.000/1.000; MedGemma 0.867/0.600 and 0.538/0.885. Disagreement (500 studies,
5,000 rows): 81.3 % agreement, 4.6 % both-wrong, 936 disagreements with MedGemma
correct 639 vs 297 for CXR.

Pilot bootstrap 95 % CIs: macro F1 0.145 [0.091, 0.205] (CXR) vs 0.216
[0.136, 0.302] (MedGemma) — overlapping. A **paired** bootstrap resolves this:
macro difference +0.071 [0.003, 0.152], p = 0.044; unigram +0.065
[0.047, 0.084], p < 0.001. The 500-study run is needed because the paired
macro result is fragile at n=120. Pilot disagreement: 81.4 % of finding rows
agree with 5.0 % error; on 223 disagreements MedGemma is right 155 times vs 68
for CXR-LLaVA. This is the selective-prediction result to extend on 500 studies.
