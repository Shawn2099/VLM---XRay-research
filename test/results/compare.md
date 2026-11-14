| metric | cxr500_t0 | medgemma500_t0 |
|---|---|---|
| images | 500 | 500 |
| successful | 500 | 500 |
| latency | mean 1.958 | p95 2.875 | max 4.713 | mean 3.606 | p95 4.376 | max 6.907 |
| report words | mean 35.8 | p95 ? | max 87 | mean 45.8 | p95 ? | max 95 |
| repetition | mean 0.0 | p95 ? | max 0.0 | mean 0.0011 | p95 ? | max 0.1034 |
| unigram F1 | 0.2141 | 0.2758 |
| macro F1 | 0.1183 | 0.1858 |
| micro P/R | P 0.138 / R 0.231 | P 0.395 / R 0.56 |

| finding F1 | cxr500_t0 | medgemma500_t0 |
|---|---|---|
| atelectasis | 0.185 | 0.322 |
| cardiomegaly | 0.225 | 0.276 |
| consolidation | 0.067 | 0.133 |
| edema | 0.094 | 0.0 |
| effusion | 0.123 | 0.353 |
| fracture | 0.125 | 0.0 |
| nodule_mass | 0.0 | 0.214 |
| normal | 0.265 | 0.56 |
| pneumonia | 0.025 | 0.0 |
| pneumothorax | 0.074 | 0.0 |
