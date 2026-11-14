# Final tables (work in progress)

500 frontal OpenI studies, greedy decoding, same API/preprocessing.

## Table 1 — Report quality

| Metric | CXR-LLaVA v1.5 | MedGemma 1.5 4B |
|---|---|---|
| Reports / failures | 500 / 0 | 500 / 0 |
| Latency mean / p95 | 1.96 s / 2.88 s | 3.61 s / 4.38 s |
| Keyword macro F1 | 0.118 | 0.186 |
| Keyword unigram F1 | 0.214 [0.205, 0.224] | 0.276 [0.268, 0.284] |
| Paired macro difference | — | +0.066 [0.010, 0.121], p=0.012 |
| CheXbert micro F1 | 0.214 | 0.251 |
| CheXbert macro F1 | 0.135 | 0.161 |
| CheXbert omission | 71.3 % | 68.5 % |
| CheXbert false-positive | 11.0 % | 9.4 % |
| RadGraph RG_ER | 0.226 | 0.293 |
| BLEU-4 | 3.56 | 4.49 |
| ROUGE-L | 0.208 | 0.216 |
| BERTScore F1 | 0.822 | 0.820 |

## Table 2 — CheXbert per finding (500 studies)

| Finding | ref+ | CXR F1 | MedGemma F1 |
|---|---|---|---|
| Enlarged Cardiomediastinum | 45 | 0.049 | 0.0 |
| Cardiomegaly | 85 | 0.323 | 0.259 |
| Lung Opacity | 87 | 0.238 | 0.267 |
| Lung Lesion | 25 | 0.0 | 0.195 |
| Edema | 7 | 0.159 | 0.25 |
| Consolidation | 12 | 0.067 | 0.0 |
| Pneumonia | 9 | 0.025 | 0.0 |
| Atelectasis | 44 | 0.165 | 0.155 |
| Pneumothorax | 5 | 0.167 | 0.0 |
| Pleural Effusion | 22 | 0.147 | 0.383 |
| Pleural Other | 9 | 0.0 | 0.2 |
| Fracture | 10 | 0.118 | 0.0 |
| Support Devices | 33 | 0.036 | 0.154 |
| No Finding | 115 | 0.391 | 0.388 |

## Table 3 — Balanced yes/no QA

| Model | Finding | n | Sensitivity | Specificity | PPV | NPV | Accuracy |
|---|---|---|---|---|---|---|---|
| CXR-LLaVA | Cardiomegaly | 60 | 0.100 | 0.967 | 0.750 | 0.518 | 0.533 |
| CXR-LLaVA | Pleural effusion | 52 | 0.000 | 1.000 | 0.000 | 0.500 | 0.500 |
| MedGemma | Cardiomegaly | 60 | 0.867 | 0.600 | 0.684 | 0.818 | 0.733 |
| MedGemma | Pleural effusion | 52 | 0.538 | 0.885 | 0.824 | 0.657 | 0.712 |

## Table 4 — Deployment

| Model | Params | VRAM | Load | Latency (report) |
|---|---|---|---|---|
| CXR-LLaVA v1.5 | 7B | 13.2 GiB | ~14 s | 1.96 s |
| MedGemma 1.5 4B | 4.3B | 8.0 GiB | ~40 s | 3.61 s |

## Table 5 — Disagreement / selective prediction

Pilot 120 studies, 1,200 finding rows:

| Quantity | Value |
|---|---|
| Models agree | 977 rows (81.4 %) |
| Both wrong when agree | 5.0 % [3.8, 6.6] |
| Disagreements | 223 rows |
| MedGemma correct | 155 |
| CXR-LLaVA correct | 68 |
| Neither correct | 0 |
| Deferral coverage | 81.4 % |
| Retained error | 5.0 % |
| No-deferral error | CXR 17.0 % / MedGemma 9.8 % |

500-study version (final):

| Quantity | Value |
|---|---|
| Models agree | 4,064 rows (81.3 %) |
| Both wrong when agree | 4.6 % [4.0, 5.3] |
| Disagreements | 936 rows |
| MedGemma correct | 639 |
| CXR-LLaVA correct | 297 |
| Neither correct | 0 |
| Deferral coverage | 81.3 % |
| Retained error | 4.6 % |
| No-deferral error | CXR 16.5 % / MedGemma 9.7 % |
