# CXR-LLaVA evaluation — temperature 0

* dataset: OpenI / IU Chest X-ray (HF mirror) [openi500]
* images: 500  ·  successful: 500  ·  errors: {}
* latency: mean 1.958 s, median 1.9 s, p95 2.875 s, max 4.713 s
* report length: 35.8 words (14–87)
* repetition (8-gram): mean 0.0, max 0.0
* unigram F1 vs reference: **0.2141**
* finding macro F1: **0.1183**  (micro P 0.138 / R 0.231)

| finding | ref+ | pred+ | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| atelectasis | 42 | 77 | 11 | 66 | 31 | 0.143 | 0.262 | 0.185 |
| cardiomegaly | 35 | 134 | 19 | 115 | 16 | 0.142 | 0.543 | 0.225 |
| consolidation | 11 | 78 | 3 | 75 | 8 | 0.038 | 0.273 | 0.067 |
| edema | 4 | 60 | 3 | 57 | 1 | 0.05 | 0.75 | 0.094 |
| effusion | 26 | 88 | 7 | 81 | 19 | 0.08 | 0.269 | 0.123 |
| pneumonia | 9 | 70 | 1 | 69 | 8 | 0.014 | 0.111 | 0.025 |
| pneumothorax | 13 | 14 | 1 | 13 | 12 | 0.071 | 0.077 | 0.074 |
| nodule_mass | 14 | 5 | 0 | 5 | 14 | 0.0 | 0.0 | 0.0 |
| fracture | 9 | 7 | 1 | 6 | 8 | 0.143 | 0.111 | 0.125 |
| normal | 210 | 92 | 40 | 52 | 170 | 0.435 | 0.19 | 0.265 |

## Sample disagreements

### false positive
* **0007 / atelectasis**
  * model: The chest radiograph reveals a region of peribronchial infiltration in the left midlung, which could be indicative of pneumonia or atelectasis due to aspiration. The lungs are otherwise clear with no evidence of central 
  * reference: the heart size and pulmonary vascularity appear within normal limits there has been clearing of left base airspace opacities the lungs now appear clear no pneumothorax or pleural effusion is seen the lungs appear hyperex
* **0009 / atelectasis**
  * model: The chest radiograph reveals low lung volumes with bronchovascular crowding. There is a presence of consolidation in the left lower lobe, which could be indicative of atelectasis or pneumonia. The cardiomediastinal and h
  * reference: the heart is normal in size and contour the lungs are clear without evidence of infiltrate there is no pneumothorax or effusion
* **0022 / atelectasis**
  * model: The radiologic report reveals a stable heart size and mediastinum. There is a presence of bilateral pleural effusions with some associated atelectasis. No pneumothorax is observed.
  * reference: images calcified granuloma right lung base heart size and pulmonary vascular engorgement appear within limits of normal mediastinal contour is unremarkable no focal consolidation pleural effusion or pneumothorax identifi
* **0026 / atelectasis**
  * model: The chest radiograph reveals a small elliptical ring shadow in the left upper lobe, which could be indicative of a lung abscess or rounded atelectasis. The lungs are otherwise clear. There is mild cardiomegaly. A small l
  * reference: the heart pulmonary and mediastinum are within normal limits there is no pleural effusion or pneumothorax there is a region of left upper lobe perihilar opacity identified

### false negative
* **0000 / atelectasis**
  * model: The radiologic report reveals a consolidation in the right lung. There is also an observation of mild cardiomegaly. The left lung appears to be grossly clear.
  * reference: there is increased opacity within the right upper lobe with possible mass and associated area of atelectasis or focal consolidation the cardiac silhouette is within normal limits opacity in the left midlung overlying the
* **0015 / atelectasis**
  * model: The chest radiograph reveals low lung volumes. The cardiac size is at the upper limit of normal. The mediastinum appears widened due to mediastinal lymphadenopathy. There are nodules present in both lungs. No evidence of
  * reference: heart is within normal limits negative for focal pulmonary consolidation pleural effusion or pneumothorax mild streaky opacity lateral right lung atelectasis versus scarring
* **0016 / atelectasis**
  * model: The chest radiograph reveals a mildly enlarged cardiac silhouette. There is no evidence of vascular congestion, pleural effusion, or acute focal pneumonia. A mild hyperexpansion of the lungs suggests the presence of chro
  * reference: no acute osseous abnormality the soft tissues are within normal limits normal appearing cardiomediastinal silhouette and hilar contours left lower lobe density representing atelectasis no focal area of consolidation pleu
* **0059 / atelectasis**
  * model: The chest radiograph reveals moderate cardiomegaly. The lungs are fully expanded and clear. A small pleural effusion is noted. There is no evidence of pneumothorax.
  * reference: there are opacities within both lung bases representing atelectasis heart size is upper limits of normal no pneumothorax no pneumothorax
