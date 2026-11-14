# Paper draft skeleton

Working title: **A reproducible open-weight pipeline for chest X-ray report
generation: comparative evaluation of CXR-LLaVA and MedGemma 1.5 4B with DICOM
preprocessing and model-disagreement analysis.**

Status: skeleton; numbers from `../PAPER_PROTOCOL.md`, `../TEST_REPORT.md`,
`../test/results/`.

## Abstract (draft)

Open-weight multimodal models can now generate chest X-ray reports, but
deployment details—DICOM windowing, model choice, and failure behaviour—are
rarely evaluated together. We present a reproducible, offline pipeline for
chest X-ray reporting on a single 24 GB GPU and compare two open-weight
backends, CXR-LLaVA v1.5 (7B) and MedGemma 1.5 4B, on 500 frontal OpenI
studies. We report CheXbert/RadGraph and text metrics with bootstrap confidence
intervals, a balanced yes/no evaluation, and a model-disagreement analysis.
MedGemma produces higher-quality structured reports but over-calls some
findings; CXR-LLaVA is faster and more conservative. When the models agree,
both are wrong on only 5 % of finding-level decisions, suggesting disagreement
as a deferral signal. Neither model is clinically usable without further
validation.

## 1. Introduction

- Chest X-ray reporting workload; open-weight VLMs are now deployable.
- Gap: papers report model metrics but not DICOM preprocessing, deployment cost,
  and disagreement/failure behaviour.
- Contributions (3): reproducible pipeline; head-to-head evaluation with
  clinical metrics; disagreement/selective-prediction analysis.
- Preview of findings.

## 2. Related work

- CXR report generation: CXR-LLaVA, CheXagent, MAIRA-2, LLaVA-Med.
- Medical multimodal models: MedGemma 1.5, Gemma 3.
- Evaluation: CheXbert, RadGraph, BLEU/ROUGE/BERTScore, reader studies.
- Selective prediction / deferral in medical AI.

## 3. Methods

### 3.1 Pipeline
- DICOM -> VOI/modality LUT -> MONOCHROME1 inversion -> 8-bit; PNG/JPEG path.
- FastAPI service, single-request lock, API/UI; models in separate images;
  one active backend on port 8000.
- Privacy: no storage; deployed offline.

### 3.2 Models
- CXR-LLaVA v1.5: ViT-L/16 + LLaMA2-7B, bf16, 13.2 GiB.
- MedGemma 1.5 4B: Gemma 3 4B medical, bf16, 8.0 GiB, dedicated venv.
- Prompts (report, differential, QA), greedy decoding.

### 3.3 Data
- OpenI 500-study frontal test set; patient/report-level dedupe; no training.
- Pilot 120 set; optional MIMIC-CXR-JPG test split; optional Saintgits reader set.

### 3.4 Metrics
- CheXbert 14-label F1, RadGraph F1, BLEU-4, ROUGE-L, BERTScore.
- Balanced QA sensitivity/specificity/PPV/NPV with Wilson CIs.
- Hallucination/omission, negation errors.
- Bootstrap CIs, paired tests, Holm correction.
- Reader study if available: 2 radiologists, 50–100 studies, 5-point scores,
  Cohen's kappa.

## 4. Results (placeholders)

**Table 1 — Report quality, 500 OpenI studies.**
CheXbert micro/macro F1, RadGraph RG_ER, BLEU-4, ROUGE-L, BERTScore, with 95 % CIs.
Pilot (120): CXR 0.256/0.143, RG_ER 0.222, BLEU 3.42, ROUGE 0.199,
BERTScore 0.820; MedGemma 0.355/0.194, RG_ER 0.296, BLEU 4.58, ROUGE 0.217,
BERTScore 0.821. **BERTScore does not separate the models** — a useful negative
result that motivates CheXbert/RadGraph as primary metrics.
500 studies: CXR CheXbert 0.214/0.135, RG_ER 0.226, BLEU 3.56, ROUGE 0.208,
BERTScore 0.822; MedGemma 0.251/0.161, RG_ER 0.293, BLEU 4.49, ROUGE 0.216,
BERTScore 0.820. CheXbert omission 71.3 % vs 68.5 %.

**Table 2 — Finding-level agreement.**
Per-finding F1/recall/precision for both models.

**Table 3 — Balanced QA.**
Sensitivity/specificity/PPV/NPV for cardiomegaly and effusion.

**Table 4 — Deployment.**
Latency mean/p95, VRAM, load time, throughput.

**Figure 1 — Disagreement/risk–coverage.**
Agreement rate vs error; who is right on disagreements.

**Table 5 — Preprocessing ablation.**
DICOM-windowed vs pre-8-bit input, 100 studies.

## 5. Discussion

- MedGemma better report structure/quality; CXR-LLaVA faster and conservative.
- Complementary errors; agreement is high-confidence; disagreement can defer.
- Deployment cost is modest; single GPU is enough for a clinic-scale pilot.
- Clinical safety: neither model is ready; false negatives on critical findings.

## 6. Limitations

- OpenI size/domain, terse references, zero-shot only.
- Keyword metrics plus CheXbert/RadGraph, but no reader study yet if unavailable.
- Lateral/multi-frame studies excluded.
- Licence constraints (CC-BY-NC, Llama-2, HAI-DEF).
- Single site/hardware.

## 7. Reproducibility

- Code, prompts, model hashes, wheel bundles, test suite; restricted weights not
  redistributed.
- Artefacts: `deploy/`, `medgemma/`, `test/`, `TEST_REPORT.md`,
  `test/results/`.

## References (starting set)

1. CXR-LLaVA, arXiv:2310.18341.
2. MedGemma 1.5 model card, Google Health AI Developer Foundations.
3. CheXbert, Smit et al., 2020.
4. RadGraph, Jain et al., 2021.
5. CheXagent, Chen et al., 2024.
6. MAIRA-2, Bannur et al., 2024.
7. CheXpert / MIMIC-CXR dataset papers.
