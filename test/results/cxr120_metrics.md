# Report metrics — report_t0

* reports: 120
* BLEU-4: 3.42
* ROUGE-L: 0.199
* CheXbert micro F1: **0.2558**
* CheXbert macro F1: **0.1425**
* RadGraph RG_ER: **0.2222** (RG_E 0.2533, complete 0.1699)

| CheXbert finding | ref+ | pred+ | TP | FP | FN | F1 |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 12 | 9 | 2 | 7 | 10 | 0.19 |
| Cardiomegaly | 22 | 42 | 15 | 27 | 7 | 0.469 |
| Lung Opacity | 27 | 23 | 4 | 19 | 23 | 0.16 |
| Lung Lesion | 4 | 5 | 1 | 4 | 3 | 0.222 |
| Edema | 3 | 11 | 1 | 10 | 2 | 0.143 |
| Consolidation | 1 | 16 | 1 | 15 | 0 | 0.118 |
| Pneumonia | 1 | 18 | 0 | 18 | 1 | 0.0 |
| Atelectasis | 14 | 23 | 5 | 18 | 9 | 0.27 |
| Pneumothorax | 4 | 3 | 0 | 3 | 4 | 0.0 |
| Pleural Effusion | 4 | 17 | 0 | 17 | 4 | 0.0 |
| Pleural Other | 1 | 0 | 0 | 0 | 1 | 0.0 |
| Fracture | 3 | 0 | 0 | 0 | 3 | 0.0 |
| Support Devices | 5 | 5 | 0 | 5 | 5 | 0.0 |
| No Finding | 32 | 39 | 15 | 24 | 17 | 0.423 |
