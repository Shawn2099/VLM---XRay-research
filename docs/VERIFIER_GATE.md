# Verifier gate â€” DenseNet-121 vs CheXbert on the reference report

* studies: 500 (OpenI-500)
* corpus: `test/data/openi500`
* labels: CheXbert positive on the reference report = 1, everything else = 0
* threshold: Youden J on the same data (reported as an upper bound, not a held-out estimate)
* trusted (AUC >= 0.80): **Pleural Effusion**

| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |
|---|---|---|---|---|---|---|---|
| Atelectasis | 30/500 | 0.683 | 0.73 | 0.20 | 0.97 | 0.27 | no |
| Cardiomegaly | 78/500 | 0.694 | 0.66 | 0.19 | 0.96 | 0.46 | no |
| Consolidation | 10/500 | 0.639 | 0.70 | 0.10 | 0.98 | 0.09 | no |
| Edema | 4/500 | â€” | 0.7 | â€” | â€” | â€” | no |
| Enlarged Cardiomediastinum | 19/500 | 0.633 | 0.65 | 0.16 | 0.96 | 0.12 | no |
| Fracture | 10/500 | 0.419 | 0.68 | 0.00 | 1.00 | 0.00 | no |
| Lung Lesion | 22/500 | 0.511 | 0.62 | 0.04 | 0.95 | 0.04 | no |
| Lung Opacity | 87/500 | 0.596 | 0.84 | 0.09 | 0.95 | 0.30 | no |
| Pleural Effusion | 18/500 | 0.850 | 0.76 | 0.44 | 0.96 | 0.31 | yes |
| Pleural Other | 7/500 | 0.574 | 0.18 | 0.00 | 0.97 | 0.00 | no |
| Pneumonia | 6/500 | 0.655 | 0.64 | 0.00 | 0.95 | 0.00 | no |
| Pneumothorax | 2/500 | â€” | 0.7 | â€” | â€” | â€” | no |
