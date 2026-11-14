# Report metrics — medgemma_t0

* reports: 120
* BLEU-4: 4.58
* ROUGE-L: 0.2173
* CheXbert micro F1: **0.3551**
* CheXbert macro F1: **0.1941**
* RadGraph RG_ER: **0.2962** (RG_E 0.3452, complete 0.225)

| CheXbert finding | ref+ | pred+ | TP | FP | FN | F1 |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 12 | 0 | 0 | 0 | 12 | 0.0 |
| Cardiomegaly | 22 | 7 | 6 | 1 | 16 | 0.414 |
| Lung Opacity | 27 | 11 | 7 | 4 | 20 | 0.368 |
| Lung Lesion | 4 | 2 | 1 | 1 | 3 | 0.333 |
| Edema | 3 | 1 | 1 | 0 | 2 | 0.5 |
| Consolidation | 1 | 0 | 0 | 0 | 1 | 0.0 |
| Pneumonia | 1 | 0 | 0 | 0 | 1 | 0.0 |
| Atelectasis | 14 | 78 | 13 | 65 | 1 | 0.283 |
| Pneumothorax | 4 | 1 | 0 | 1 | 4 | 0.0 |
| Pleural Effusion | 4 | 8 | 2 | 6 | 2 | 0.333 |
| Pleural Other | 1 | 0 | 0 | 0 | 1 | 0.0 |
| Fracture | 3 | 0 | 0 | 0 | 3 | 0.0 |
| Support Devices | 5 | 1 | 0 | 1 | 5 | 0.0 |
| No Finding | 32 | 79 | 27 | 52 | 5 | 0.486 |
