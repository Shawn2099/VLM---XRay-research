# Report metrics — cxr500_t0

* reports: 500
* BLEU-4: 3.56
* ROUGE-L: 0.2078
* CheXbert micro F1: **0.2139**
* CheXbert macro F1: **0.1346**
* CheXbert omission rate: 0.7126
* CheXbert false-positive/hallucination rate: 0.1095
* RadGraph RG_ER: **0.2255** (RG_E 0.2621, complete 0.1704)
* BERTScore F1: 0.8216

| CheXbert finding | ref+ | pred+ | TP | FP | FN | F1 |
|---|---|---|---|---|---|---|
| Enlarged Cardiomediastinum | 45 | 36 | 2 | 34 | 43 | 0.049 |
| Cardiomegaly | 85 | 175 | 42 | 133 | 43 | 0.323 |
| Lung Opacity | 87 | 56 | 17 | 39 | 70 | 0.238 |
| Lung Lesion | 25 | 7 | 0 | 7 | 25 | 0.0 |
| Edema | 7 | 56 | 5 | 51 | 2 | 0.159 |
| Consolidation | 12 | 77 | 3 | 74 | 9 | 0.067 |
| Pneumonia | 9 | 71 | 1 | 70 | 8 | 0.025 |
| Atelectasis | 44 | 89 | 11 | 78 | 33 | 0.165 |
| Pneumothorax | 5 | 7 | 1 | 6 | 4 | 0.167 |
| Pleural Effusion | 22 | 87 | 8 | 79 | 14 | 0.147 |
| Pleural Other | 9 | 6 | 0 | 6 | 9 | 0.0 |
| Fracture | 10 | 7 | 1 | 6 | 9 | 0.118 |
| Support Devices | 33 | 22 | 1 | 21 | 32 | 0.036 |
| No Finding | 115 | 161 | 54 | 107 | 61 | 0.391 |
