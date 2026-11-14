# Verifier gate — DenseNet-121 vs CheXbert on the reference report

* studies: 500 (OpenI-500)
* corpus: `test/data/openi500`
* labels: CheXbert positive on the reference report = 1, everything else = 0
* threshold: Youden J on the same data (reported as an upper bound, not a held-out estimate)
* trusted (AUC >= 0.80): **Pleural Effusion**

| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |
|---|---|---|---|---|---|---|---|
| Atelectasis | 30/500 | 0.710 | 0.46 | 0.70 | 0.64 | 0.11 | no |
| Cardiomegaly | 78/500 | 0.744 | 0.18 | 0.70 | 0.68 | 0.29 | no |
| Consolidation | 10/500 | 0.666 | 0.52 | 0.60 | 0.70 | 0.04 | no |
| Edema | 4/500 | — | 0.7 | — | — | — | no |
| Enlarged Cardiomediastinum | 19/500 | 0.554 | 0.47 | 0.68 | 0.56 | 0.05 | no |
| Fracture | 10/500 | 0.539 | 0.27 | 0.80 | 0.37 | 0.03 | no |
| Lung Lesion | 22/500 | 0.533 | 0.30 | 1.00 | 0.15 | 0.05 | no |
| Lung Opacity | 87/500 | 0.573 | 0.52 | 0.79 | 0.34 | 0.20 | no |
| Pleural Effusion | 18/500 | 0.822 | 0.49 | 0.78 | 0.81 | 0.12 | yes |
| Pleural Other | 7/500 | 0.574 | 0.31 | 0.86 | 0.43 | 0.02 | no |
| Pneumonia | 6/500 | 0.636 | 0.21 | 0.83 | 0.54 | 0.02 | no |
| Pneumothorax | 2/500 | — | 0.7 | — | — | — | no |
