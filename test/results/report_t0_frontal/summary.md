# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 74  ·  successful: 74  ·  errors: {}
* latency: mean 2.068 s, median 2.01 s, p95 3.016 s, max 3.19 s
* report length: 37.4 words (18–60)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.2086**
* finding macro F1: **0.0955**  (micro P 0.154 / R 0.25)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 6 | 14 | 1 | 13 | 5 | 0.071 | 0.167 | 0.1 |
| cardiomegaly | 4 | 22 | 3 | 19 | 1 | 0.136 | 0.75 | 0.231 |
| consolidation | 1 | 12 | 1 | 11 | 0 | 0.083 | 1.0 | 0.154 |
| edema | 0 | 8 | 0 | 8 | 0 | 0.0 | 0.0 | 0.0 |
| effusion | 3 | 12 | 0 | 12 | 3 | 0.0 | 0.0 | 0.0 |
| pneumonia | 2 | 14 | 1 | 13 | 1 | 0.071 | 0.5 | 0.125 |
| pneumothorax | 3 | 2 | 0 | 2 | 3 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 1 | 3 | 0 | 3 | 1 | 0.0 | 0.0 | 0.0 |
| fracture | 3 | 0 | 0 | 0 | 3 | 0.0 | 0.0 | 0.0 |
| normal | 41 | 17 | 10 | 7 | 31 | 0.588 | 0.244 | 0.345 |

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
* **0034 / atelectasis**
  * model: The chest radiograph shows mild cardiomegaly and a tortuous aorta. The lungs are hyperinflated with no evidence of pneumothorax or pleural effusion. Bibasilar opacities, larger on the right side, are likely indicative of
  * reference: the lungs are hyperexpanded heart size normal no mass or focal opacities seen stable degenerative changes of the thoracic spine

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
