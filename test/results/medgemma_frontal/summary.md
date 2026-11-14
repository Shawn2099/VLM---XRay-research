# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 74  ·  successful: 74  ·  errors: {}
* latency: mean 3.603 s, median 3.592 s, p95 4.405 s, max 5.245 s
* report length: 45.7 words (25–66)
* repetition (8-gram): mean 0.0013, max 0.0345
* unigram F1 vs reference: **0.2774**
* finding macro F1: **0.1643**  (micro P 0.493 / R 0.578)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 6 | 6 | 2 | 4 | 4 | 0.333 | 0.333 | 0.333 |
| cardiomegaly | 4 | 1 | 1 | 0 | 3 | 1.0 | 0.25 | 0.4 |
| consolidation | 1 | 1 | 0 | 1 | 1 | 0.0 | 0.0 | 0.0 |
| edema | 0 | 1 | 0 | 1 | 0 | 0.0 | 0.0 | 0.0 |
| effusion | 3 | 5 | 1 | 4 | 2 | 0.2 | 0.333 | 0.25 |
| pneumonia | 2 | 0 | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 3 | 1 | 0 | 1 | 3 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 1 | 1 | 0 | 1 | 1 | 0.0 | 0.0 | 0.0 |
| fracture | 3 | 0 | 0 | 0 | 3 | 0.0 | 0.0 | 0.0 |
| normal | 41 | 59 | 33 | 26 | 8 | 0.559 | 0.805 | 0.66 |

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
* **0052 / atelectasis**
  * model: Findings:
Lungs: The right lung is opacified, consistent with a large pleural effusion. The left lung is clear.
Pleura: Right pleural effusion.
Heart: Normal size.
Mediastinum: Normal.
Bones: Normal.
Atelectasis: Not pre
  * reference: borderline enlarged heart stable mediastinal contours aortic calcifications hyperinflated lungs with chronic appearing interstitial markings compatible with emphysema bilateral streaky opacities increased vascularity com
* **0095 / atelectasis**
  * model: FINDINGS:
LUNGS: There is a right pleural effusion. There is left lower lobe atelectasis.
PLEURA: Right pleural effusion.
HEART: Heart size is normal.
MESENTERIUM: No free air.
BONES: No acute bony abnormality.
IMPRESSIO
  * reference: cardiac silhouette is enlarged but unchanged there is leftsided central line with a lumen poly vasculature is within normal limits mediastinum is normal bibasilar opacity left greater than right is appreciated no pneumot

### false negative
* **0000 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pneumothorax. There is no pulmonary edema.
Pleura: No pleural effusion is identified.
Heart: The heart size is normal.
Mediastinum: The me
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
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
* **0027 / atelectasis**
  * model: Findings:
Lungs: The lungs are clear without focal consolidation, atelectasis, or pulmonary edema.
Pleura: No pleural effusion or pneumothorax is identified.
Heart: The heart size is normal.
Mediastinum: The mediastinal 
  * reference: there is minimal opacity in the left lung base representing atelectasis the lungs are otherwise clear heart size is normal no pneumothorax
