# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror)
* images: 5  ·  successful: 5  ·  errors: {}
* latency: mean 1.822 s, median 1.725 s, p95 2.503 s, max 2.503 s
* report length: 35.2 words (26–54)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.1771**
* finding macro F1: **0.0667**  (micro P 0.167 / R 0.2)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 1 | 1 | 0 | 1 | 1 | 0.0 | 0.0 | 0.0 |
| cardiomegaly | 0 | 1 | 0 | 1 | 0 | 0.0 | 0.0 | 0.0 |
| consolidation | 1 | 2 | 1 | 1 | 0 | 0.5 | 1.0 | 0.667 |
| edema | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| effusion | 0 | 1 | 0 | 1 | 0 | 0.0 | 0.0 | 0.0 |
| pneumonia | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| pneumothorax | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| nodule_mass | 1 | 0 | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| fracture | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| normal | 2 | 1 | 0 | 1 | 2 | 0.0 | 0.0 | 0.0 |

## Sample disagreements

### false positive
* **0001 / atelectasis**
  * model: The chest radiograph shows a small left pleural effusion. There is also mild left lung base atelectasis and trace right pleural effusion. No pulmonary edema or pneumonia is seen. The cardiomediastinal silhouette is norma
  * reference: interstitial markings are diffusely prominent throughout both lungs heart size is normal pulmonary normal
* **0000 / cardiomegaly**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0004 / consolidation**
  * model: The chest radiograph reveals a region of peribronchial infiltration in the left lower lobe. The lungs elsewhere are unremarkable with no evidence of cardiac decompensation. There is central adenopathy, predominantly in t
  * reference: heart size and mediastinal contours are normal in appearance no consolidative airspace opacities no radiographic evidence of pleural effusion or pneumothorax visualized osseous structures appear intact
* **0001 / effusion**
  * model: The chest radiograph shows a small left pleural effusion. There is also mild left lung base atelectasis and trace right pleural effusion. No pulmonary edema or pneumonia is seen. The cardiomediastinal silhouette is norma
  * reference: interstitial markings are diffusely prominent throughout both lungs heart size is normal pulmonary normal

### false negative
* **0000 / atelectasis**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0000 / nodule_mass**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0000 / normal**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0002 / normal**
  * model: The chest x-ray shows clear lungs without any focal consolidation, pleural effusion, or pneumothorax. The heart size is normal, and the mediastinal silhouette and hilar contours are also normal.
  * reference: cardiac and mediastinal contours are within normal limits the lungs are clear bony structures are intact
