# Verifier gate â€” DenseNet-121 vs CheXbert on the reference report

* studies: 500 (OpenI-500)
* corpus: `test/data/openi500`
* labels: CheXbert positive on the reference report = 1, everything else = 0
* threshold: Youden J on the same data (reported as an upper bound, not a held-out estimate)
* trusted (AUC >= 0.80): **Pleural Effusion**

| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |
|---|---|---|---|---|---|---|---|
| Atelectasis | 30/500 | 0.674 | 0.77 | 0.40 | 0.90 | 0.18 | no |
| Cardiomegaly | 78/500 | 0.610 | 0.69 | 0.56 | 0.60 | 0.20 | no |
| Consolidation | 10/500 | 0.619 | 0.54 | 0.50 | 0.79 | 0.05 | no |
| Edema | 4/500 | â€” | 0.7 | â€” | â€” | â€” | no |
| Enlarged Cardiomediastinum | 19/500 | 0.622 | 0.52 | 0.79 | 0.43 | 0.05 | no |
| Fracture | 10/500 | 0.399 | 0.07 | 1.00 | 0.04 | 0.02 | no |
| Lung Lesion | 22/500 | 0.466 | 0.12 | 0.95 | 0.11 | 0.04 | no |
| Lung Opacity | 87/500 | 0.601 | 0.55 | 0.78 | 0.43 | 0.22 | no |
| Pleural Effusion | 18/500 | 0.826 | 0.64 | 0.94 | 0.63 | 0.09 | yes |
| Pneumonia | 6/500 | 0.711 | 0.52 | 1.00 | 0.58 | 0.03 | no |
| Pneumothorax | 2/500 | â€” | 0.7 | â€” | â€” | â€” | no |
