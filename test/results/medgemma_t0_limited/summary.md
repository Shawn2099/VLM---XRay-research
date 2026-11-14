# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 1  ·  successful: 1  ·  errors: {}
* latency: mean 3.721 s, median 3.721 s, p95 3.721 s, max 3.721 s
* report length: 46 words (46–46)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.2**
* finding macro F1: **0.1**  (micro P 1.0 / R 0.25)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 1 | 0 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| cardiomegaly | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| consolidation | 1 | 0 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| edema | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| effusion | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| pneumonia | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 1 | 0 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| fracture | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| normal | 1 | 1 | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |

## Sample disagreements

### false positive

### false negative
* **0000 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0000 / consolidation**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0000 / nodule_mass**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
