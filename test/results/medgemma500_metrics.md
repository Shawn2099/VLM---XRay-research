# Report metrics — medgemma500_t0

* reports: 500
* BLEU-4: 4.49
* ROUGE-L: 0.2158
* CheXbert micro F1: **0.2506**
* CheXbert macro F1: **0.1608**
* CheXbert omission rate: 0.685
* CheXbert false-positive/hallucination rate: 0.0938
* RadGraph RG_ER: **0.2933** (RG_E 0.3483, complete 0.2203)
* BERTScore F1: 0.8202

| CheXbert finding | ref+ | pred+ | TP | FP | FN | F1 |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 45 | 0 | 0 | 0 | 45 | 0.0 |
| Cardiomegaly | 85 | 23 | 14 | 9 | 71 | 0.259 |
| Lung Opacity | 87 | 48 | 18 | 30 | 69 | 0.267 |
| Lung Lesion | 25 | 16 | 4 | 12 | 21 | 0.195 |
| Edema | 7 | 1 | 1 | 0 | 6 | 0.25 |
| Consolidation | 12 | 1 | 0 | 1 | 12 | 0.0 |
| Pneumonia | 9 | 0 | 0 | 0 | 9 | 0.0 |
| Atelectasis | 44 | 355 | 31 | 324 | 13 | 0.155 |
| Pneumothorax | 5 | 1 | 0 | 1 | 5 | 0.0 |
| Pleural Effusion | 22 | 25 | 9 | 16 | 13 | 0.383 |
| Pleural Other | 9 | 1 | 1 | 0 | 8 | 0.2 |
| Fracture | 10 | 0 | 0 | 0 | 10 | 0.0 |
| Support Devices | 33 | 6 | 3 | 3 | 30 | 0.154 |
| No Finding | 115 | 292 | 79 | 213 | 36 | 0.388 |
