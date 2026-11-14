# CXR-LLaVA evaluation — temperature 0.2

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 30  ·  successful: 30  ·  errors: {}
* latency: mean 1.993 s, median 1.953 s, p95 2.594 s, max 2.881 s
* report length: 36.0 words (21–54)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.1967**
* finding macro F1: **0.0834**  (micro P 0.158 / R 0.214)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 5 | 5 | 1 | 4 | 4 | 0.2 | 0.2 | 0.2 |
| cardiomegaly | 1 | 6 | 0 | 6 | 1 | 0.0 | 0.0 | 0.0 |
| consolidation | 1 | 6 | 1 | 5 | 0 | 0.167 | 1.0 | 0.286 |
| edema | 0 | 5 | 0 | 5 | 0 | 0.0 | 0.0 | 0.0 |
| effusion | 3 | 5 | 0 | 5 | 3 | 0.0 | 0.0 | 0.0 |
| pneumonia | 0 | 3 | 0 | 3 | 0 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 1 | 0 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 1 | 1 | 0 | 1 | 1 | 0.0 | 0.0 | 0.0 |
| fracture | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| normal | 16 | 7 | 4 | 3 | 12 | 0.571 | 0.25 | 0.348 |

## Sample disagreements

### false positive
* **0001 / atelectasis**
  * model: The chest radiograph shows a small left pleural effusion. There is also mild left lung base atelectasis and trace right pleural effusion. No pulmonary edema is seen. The cardiomediastinal silhouette is normal in size.
  * reference: interstitial markings are diffusely prominent throughout both lungs heart size is normal pulmonary normal
* **0010 / atelectasis**
  * model: The radiologic report reveals a mildly enlarged heart with stable mediastinal and hilar contours. There is no evidence of pleural effusion or pneumothorax. A streaky left basilar opacity is observed, which is most consis
  * reference: the cardiomediastinal silhouette is normal in size and contour no focal consolidation pneumothorax or large pleural effusion calcified granuloma right base normal
* **0015 / atelectasis**
  * model: The radiologic report reveals consolidation in the right lower lobe of the lungs. There is also evidence of atelectasis in the left lower lobe. The heart shows moderate cardiomegaly. Pulmonary vascular engorgement is als
  * reference: the heart is normal size the mediastinum is unremarkable a tortuous calcified thoracic aorta is present the lungs are hyperexpanded consistent with emphysema there is no pleural effusion pneumothorax or focal airspace di
* **0029 / atelectasis**
  * model: The chest radiograph reveals a right-sided prepectoral Port-A-Cath in situ with the tip at the cavoatrial junction. There is no evidence of pneumothorax. The cardiomediastinal shadow appears normal. No signs of pulmonary
  * reference: heart size and mediastinal contour are normal pulmonary vascularity is normal lungs are clear no pleural effusions or pneumothoraces

### false negative
* **0000 / atelectasis**
  * model: The radiologic report reveals severe consolidation in the right lung. There is also moderate cardiomegaly and mediastinal vascular engorgement, along with mild pulmonary edema. A small right pleural effusion is presumed.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0013 / atelectasis**
  * model: The radiologic report reveals a moderately enlarged heart with unremarkable mediastinal contours. Mild pulmonary edema is present, along with a probable small left pleural effusion. No focal consolidation or pneumothorax
  * reference: the cardiomediastinal silhouette and vasculature are within normal limits for size and contour lung volumes are low with central bronchovascular crowding and patchy basilar atelectasis degenerative changes of the spine
* **0017 / atelectasis**
  * model: The chest radiograph shows no acute abnormality in the lungs, mediastinum, heart, or thorax. The cardiomediastinal and hilar contours are normal. The lung fields are clear without any evidence of pneumothorax, fracture, 
  * reference: normal cardiomediastinal silhouette interval improvement in lung volumes bilaterally improved aeration of the right and left lung bases bilateral small pleural effusions and left base atelectatic change with interval imp
* **0027 / atelectasis**
  * model: The chest radiograph reveals hyperinflated lungs with flattening of the diaphragms, indicative of chronic obstructive pulmonary disease. There is no evidence of focal consolidation, pleural effusion, or pneumothorax. The
  * reference: there is minimal opacity in the left lung base representing atelectasis the lungs are otherwise clear heart size is normal no pneumothorax
