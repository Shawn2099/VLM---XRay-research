# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 120  ·  successful: 120  ·  errors: {}
* latency: mean 2.012 s, median 1.939 s, p95 3.039 s, max 3.828 s
* report length: 36.5 words (18–72)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.2092**
* finding macro F1: **0.15**  (micro P 0.207 / R 0.315)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 13 | 23 | 4 | 19 | 9 | 0.174 | 0.308 | 0.222 |
| cardiomegaly | 12 | 37 | 10 | 27 | 2 | 0.27 | 0.833 | 0.408 |
| consolidation | 1 | 16 | 1 | 15 | 0 | 0.062 | 1.0 | 0.118 |
| edema | 1 | 11 | 0 | 11 | 1 | 0.0 | 0.0 | 0.0 |
| effusion | 7 | 19 | 0 | 19 | 7 | 0.0 | 0.0 | 0.0 |
| pneumonia | 2 | 18 | 1 | 17 | 1 | 0.056 | 0.5 | 0.1 |
| pneumothorax | 4 | 4 | 0 | 4 | 4 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 2 | 5 | 1 | 4 | 1 | 0.2 | 0.5 | 0.286 |
| fracture | 4 | 0 | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| normal | 62 | 31 | 17 | 14 | 45 | 0.548 | 0.274 | 0.366 |

## Sample disagreements

### false positive
* **0001 / atelectasis**
  * model: The chest radiograph shows a small left pleural effusion. There is also mild left lung base atelectasis and trace right pleural effusion. No pulmonary edema or pneumonia is seen. The cardiomediastinal silhouette is norma
  * reference: interstitial markings are diffusely prominent throughout both lungs heart size is normal pulmonary normal
* **0010 / atelectasis**
  * model: The radiologic report reveals a mildly enlarged heart with stable mediastinal and hilar contours. There is no evidence of pleural effusion or pneumothorax. A streaky left basilar opacity is observed, which is most consis
  * reference: the cardiomediastinal silhouette is normal in size and contour no focal consolidation pneumothorax or large pleural effusion calcified granuloma right base normal
* **0015 / atelectasis**
  * model: The radiologic report reveals a mildly enlarged heart with normal hilar contours. The mediastinal contour is minimally prominent. There are no signs of pneumothorax or pleural effusion. Bibasilar atelectasis is present, 
  * reference: the heart is normal size the mediastinum is unremarkable a tortuous calcified thoracic aorta is present the lungs are hyperexpanded consistent with emphysema there is no pleural effusion pneumothorax or focal airspace di
* **0016 / atelectasis**
  * model: The radiologic report reveals a mildly enlarged heart with normal mediastinal contours. The pulmonary vasculature is also normal. However, there is a patchy opacity in the right lung base which could be indicative of ear
  * reference: lucency crosses the th left posterior rib visualized portions of the thoracic spine are unremarkable mediastinal contours are normal lungs are clear there is no pneumothorax or large pleural effusion

### false negative
* **0000 / atelectasis**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0017 / atelectasis**
  * model: The chest radiograph shows a mildly enlarged heart with mild unfolding and calcification along the aorta. The lungs appear clear without any pleural effusions or pneumothorax. Mild-to-moderate degenerative changes are no
  * reference: normal cardiomediastinal silhouette interval improvement in lung volumes bilaterally improved aeration of the right and left lung bases bilateral small pleural effusions and left base atelectatic change with interval imp
* **0027 / atelectasis**
  * model: The chest radiograph reveals hyperinflated lungs with flattening of the diaphragms, indicative of chronic obstructive pulmonary disease. There is no evidence of focal consolidation, pleural effusion, or pneumothorax. The
  * reference: there is minimal opacity in the left lung base representing atelectasis the lungs are otherwise clear heart size is normal no pneumothorax
* **0037 / atelectasis**
  * model: The chest radiograph reveals low lung volumes. The cardiac size is at the upper limit of normal. The mediastinum appears widened due to mediastinal lymphadenopathy. There are nodules present in both lungs. No evidence of
  * reference: heart is within normal limits negative for focal pulmonary consolidation pleural effusion or pneumothorax mild streaky opacity lateral right lung atelectasis versus scarring
