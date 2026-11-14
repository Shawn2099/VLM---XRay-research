# Verifier gate â€” DenseNet-121 vs CheXbert on the reference report

* studies: 500 (OpenI-500)
* corpus: `test/data/openi500`
* labels: CheXbert positive on the reference report = 1, everything else = 0
* threshold: Youden J on the same data (reported as an upper bound, not a held-out estimate)
* trusted (AUC >= 0.80): **Pleural Effusion**

| Finding | pos/n | AUC | threshold | sens | spec | PPV | trusted |
|---|---|---|---|---|---|---|---|
| Atelectasis | 30/500 | 0.683 | inf | 0.00 | 1.00 | 0.00 | no |
| Cardiomegaly | 78/500 | 0.694 | inf | 0.00 | 1.00 | 0.00 | no |
| Consolidation | 10/500 | 0.639 | inf | 0.00 | 1.00 | 0.00 | no |
| Edema | 4/500 | â€” | 0.7 | â€” | â€” | â€” | no |
| Enlarged Cardiomediastinum | 19/500 | 0.633 | inf | 0.00 | 1.00 | 0.00 | no |
| Fracture | 10/500 | 0.419 | inf | 0.00 | 1.00 | 0.00 | no |
| Lung Lesion | 22/500 | 0.511 | inf | 0.00 | 1.00 | 0.00 | no |
| Lung Opacity | 87/500 | 0.596 | inf | 0.00 | 1.00 | 0.00 | no |
| Pleural Effusion | 18/500 | 0.850 | inf | 0.00 | 1.00 | 0.00 | yes |
| Pleural Other | 7/500 | 0.574 | inf | 0.00 | 1.00 | 0.00 | no |
| Pneumonia | 6/500 | 0.655 | inf | 0.00 | 1.00 | 0.00 | no |
| Pneumothorax | 2/500 | â€” | 0.7 | â€” | â€” | â€” | no |
