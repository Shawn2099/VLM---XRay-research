# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 120  ·  successful: 120  ·  errors: {}
* latency: mean 3.567 s, median 3.504 s, p95 4.535 s, max 5.139 s
* report length: 45.5 words (25–66)
* repetition (8-gram): mean 0.0008, max 0.0345
* unigram F1 vs reference: **0.2748**
* finding macro F1: **0.2283**  (micro P 0.467 / R 0.583)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 13 | 11 | 3 | 8 | 10 | 0.273 | 0.231 | 0.25 |
| cardiomegaly | 12 | 7 | 6 | 1 | 6 | 0.857 | 0.5 | 0.632 |
| consolidation | 1 | 2 | 0 | 2 | 1 | 0.0 | 0.0 | 0.0 |
| edema | 1 | 3 | 0 | 3 | 1 | 0.0 | 0.0 | 0.0 |
| effusion | 7 | 8 | 2 | 6 | 5 | 0.25 | 0.286 | 0.267 |
| pneumonia | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 4 | 3 | 0 | 3 | 4 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 2 | 2 | 1 | 1 | 1 | 0.5 | 0.5 | 0.5 |
| fracture | 4 | 0 | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| normal | 62 | 99 | 51 | 48 | 11 | 0.515 | 0.823 | 0.634 |

## Sample disagreements

### false positive
* **0034 / atelectasis**
  * model: FINDINGS:
LUNGS: No focal consolidation, pleural effusion, or pneumothorax. There is linear atelectasis in the right lower lobe.
PLEURA: No pleural effusion or pneumothorax.
HEART: The heart size is normal.
MESENTERIUM: 
  * reference: the lungs are hyperexpanded heart size normal no mass or focal opacities seen stable degenerative changes of the thoracic spine
* **0042 / atelectasis**
  * model: Findings:
Lungs: Bilateral lower lobe atelectasis.
Pleura: No pleural effusion or pneumothorax.
Heart: Normal heart size.
Mediastinum: Normal.
Bones: Normal.
Impression: Bilateral lower lobe atelectasis.
  * reference: heart is large pulmonary are engorged bibasilar interstitial infiltrates and bilateral costophrenic blunting are present
* **0044 / atelectasis**
  * model: Findings:
Lungs: Bilateral pleural effusions, right greater than left, obscuring the right hemidiaphragm and right costophrenic angle. Right lower lobe atelectasis. Left lower lobe atelectasis.
Pleura: Bilateral pleural 
  * reference: there is stable cardiomegaly with pulmonary vascular congestion and probable mild interstitial edema there are bilateral pleural effusions with bibasilar airspace disease right greater than left there is no pneumothorax 
* **0049 / atelectasis**
  * model: FINDINGS:
LUNGS: No focal consolidation, pleural effusion, or pneumothorax. There is mild atelectasis in the right lung base.
PLEURA: No pleural effusion or pneumothorax.
HEART: The heart size is normal.
MESENTERIUM: The
  * reference: low lung volumes with bronchovascular crowding sequela of prior granulomatous disease otherwise lungs clear heart size normal stable severe l deformity

### false negative
* **0000 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0008 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear. No atelectasis, consolidation, pulmonary edema, or pneumothorax is identified.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal. No cardiomegaly is identifi
  * reference: the heart is again mildly enlarged mediastinal contours are stable patient is somewhat rotated the lungs are hypoinflated with elevated left hemidiaphragm opacities compatible with atelectasis no large effusion is seen t
* **0013 / atelectasis**
  * model: FINDINGS:
Lungs: The right lung is collapsed. The left lung is clear. Pleura: No pleural effusion or pneumothorax. Heart: The heart size is normal. Mediastinum: The mediastinum is normal. Bones: The bones are normal. IMP
  * reference: the cardiomediastinal silhouette and vasculature are within normal limits for size and contour lung volumes are low with central bronchovascular crowding and patchy basilar atelectasis degenerative changes of the spine
* **0017 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear. There is no evidence of consolidation, atelectasis, pulmonary edema, or pneumothorax.
Pleura: There is a small left pleural effusion.
Heart: The heart size is normal. There is no evi
  * reference: normal cardiomediastinal silhouette interval improvement in lung volumes bilaterally improved aeration of the right and left lung bases bilateral small pleural effusions and left base atelectatic change with interval imp
