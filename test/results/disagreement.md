# Model disagreement — cxr500_t0 vs medgemma500_t0

* studies: 500
* finding-level rows: 5000
* models agree: 4064 rows (81.3%) · both-wrong rate **4.6%** (95% CI (0.04, 0.053))
* models disagree: 936 rows · left correct 297, right correct 639, neither 0
* overall finding error: left **16.5%**, right **9.7%**
* if every disagreement is deferred: coverage 81.3%, retained (agreed) error 4.6%; no-deferral error left 16.5% / right 9.7%

| finding | both+ | both- | left only | right only | left correct | right correct | neither |
|---|---|---|---|---|---|---|---|
| atelectasis | 8 | 386 | 69 | 37 | 34 | 72 | 0 |
| cardiomegaly | 13 | 356 | 121 | 10 | 21 | 110 | 0 |
| consolidation | 1 | 419 | 77 | 3 | 5 | 75 | 0 |
| edema | 2 | 439 | 58 | 1 | 4 | 55 | 0 |
| effusion | 10 | 397 | 78 | 15 | 13 | 80 | 0 |
| pneumonia | 0 | 430 | 70 | 0 | 1 | 69 | 0 |
| pneumothorax | 0 | 482 | 14 | 4 | 5 | 13 | 0 |
| nodule_mass | 1 | 482 | 4 | 13 | 10 | 7 | 0 |
| fracture | 0 | 493 | 7 | 0 | 1 | 6 | 0 |
| normal | 74 | 71 | 18 | 337 | 203 | 152 | 0 |
