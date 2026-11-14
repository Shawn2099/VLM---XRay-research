# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror) [openi500]
* images: 500  ·  successful: 500  ·  errors: {}
* latency: mean 3.606 s, median 3.562 s, p95 4.376 s, max 6.907 s
* report length: 45.8 words (23–95)
* repetition (8-gram): mean 0.0011, max 0.1034
* unigram F1 vs reference: **0.2758**
* finding macro F1: **0.1858**  (micro P 0.395 / R 0.56)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 42 | 45 | 14 | 31 | 28 | 0.311 | 0.333 | 0.322 |
| cardiomegaly | 35 | 23 | 8 | 15 | 27 | 0.348 | 0.229 | 0.276 |
| consolidation | 11 | 4 | 1 | 3 | 10 | 0.25 | 0.091 | 0.133 |
| edema | 4 | 3 | 0 | 3 | 4 | 0.0 | 0.0 | 0.0 |
| effusion | 26 | 25 | 9 | 16 | 17 | 0.36 | 0.346 | 0.353 |
| pneumonia | 9 | 0 | 0 | 0 | 9 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 13 | 4 | 0 | 4 | 13 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 14 | 14 | 3 | 11 | 11 | 0.214 | 0.214 | 0.214 |
| fracture | 9 | 0 | 0 | 0 | 9 | 0.0 | 0.0 | 0.0 |
| normal | 210 | 411 | 174 | 237 | 36 | 0.423 | 0.829 | 0.56 |

## Sample disagreements

### false positive
* **0051 / atelectasis**
  * model: Findings:
Lungs: The left lung is clear. There is a moderate right pleural effusion with associated atelectasis of the right lower lobe.
Pleura: Right pleural effusion.
Heart: The heart size is normal.
Mediastinum: The m
  * reference: the heart size is within normal limits there are calcified hilar lymph bilaterally there are bibasilar airspace opacities with small bilateral pleural effusions left greater than right no pneumothorax no acute bony abnor
* **0052 / atelectasis**
  * model: Findings:
Lungs: No focal consolidation, pleural effusion, or pneumothorax. There is linear atelectasis in the left lung base.
Pleura: No pleural effusion or pneumothorax.
Heart: The heart size is normal.
Mediastinum: Th
  * reference: the lungs are clear no pleural effusion is seen the heart and mediastinum are normal arthritic changes of the spine are present
* **0054 / atelectasis**
  * model: Findings:
Lungs: The right lung appears clear. The left lung demonstrates mild atelectasis in the lower lobe. No focal consolidation, pleural effusion, or pneumothorax is identified.
Pleura: No pleural effusion or pneumo
  * reference: the heart is normal in size the mediastinum is unremarkable the lungs are hypoinflated with opacities in the lung bases bronchovascular crowding no focal consolidation or pleural effusion are seen
* **0066 / atelectasis**
  * model: Findings:
Lungs: There is linear atelectasis in the left upper lobe. The right lung is clear.
Pleura: No pleural effusion or pneumothorax.
Heart: Normal heart size.
Mediastinum: Normal.
Bones: Normal.
Impression: Left up
  * reference: cardiac and mediastinal contours are unremarkable pulmonary vascularity is within normal limits no focal air space opacities pleural effusion or pneumothorax there are increased lucencies in the bilateral apices along wi

### false negative
* **0000 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0005 / atelectasis**
  * model: FINDINGS:
Lungs: The right lung is collapsed. The left lung is clear. Pleura: No pleural effusion or pneumothorax. Heart: The heart size is normal. Mediastinum: The mediastinum is normal. Bones: The bones are normal. IMP
  * reference: the cardiomediastinal silhouette and vasculature are within normal limits for size and contour lung volumes are low with central bronchovascular crowding and patchy basilar atelectasis degenerative changes of the spine
* **0016 / atelectasis**
  * model: FINDINGS:
LUNGS: No focal consolidation, pleural effusion, or pneumothorax. No atelectasis.
PLEURA: No pleural effusion or pneumothorax.
HEART: Normal size.
MESENTERIUM: No free air.
BONES: No acute fracture.
IMPRESSION:
  * reference: no acute osseous abnormality the soft tissues are within normal limits normal appearing cardiomediastinal silhouette and hilar contours left lower lobe density representing atelectasis no focal area of consolidation pleu
* **0059 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear. No focal consolidation, atelectasis, pulmonary edema, or pneumothorax is identified.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal. No cardiomegaly is id
  * reference: there are opacities within both lung bases representing atelectasis heart size is upper limits of normal no pneumothorax no pneumothorax
