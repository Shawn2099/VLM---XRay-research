# TrustMed — end-to-end validation

Everything below was run on this machine against the live services on
2026-11-15. Nothing here is projected; where a number is missing it says so.

## 1. What is running

| Piece | Where | State |
|---|---|---|
| Report service | `10.10.10.28:8000` (MedGemma 1.5 4B active) | healthy, 8.0 GiB VRAM |
| TrustMed web | `127.0.0.1:8010` (FastAPI, CPU) | healthy |
| Store | `data_trustmed/trustmed.db` (SQLite, WAL) | 8 tables |
| Verifier | CheXbert 0.0.2 + TorchXRayVision DenseNet-121, CPU | loaded |

## 2. Functional tests

| Suite | Result | Notes |
|---|---|---|
| `test/trustmed_e2e.py` | **29/29 pass** | login, upload, generate, read-back, review, invalid action, history, self-tests |
| `test/trustmed_ingest.py` | **6/6 pass** | DICOM accepted, 16-bit PNG refused, colour photo refused, garbage refused, PNG accepted, hash dedupe |
| Auth | pass | unauthenticated upload → 401, wrong password → 401, radiologist-only review → 403 for clinicians |

Latency, end-to-end through TrustMed (image already uploaded):

| Run | Latency |
|---|---|
| MedGemma backend | 3.9 – 4.6 s |
| Breakdown | generation ≈ 3.6 s (remote GPU) · CheXbert ≈ 0.35 s · DenseNet ≈ 0.12 s |

## 3. Bugs found by the tests, and the fix

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | only 2 findings per report | CheXbert `classification` returns **0 for "absent"**; the code treated 0 as "not mentioned" and dropped every negative | map `1→present`, `0→absent`, `−1→hedged`, `''→not mentioned` (G5) |
| 2 | "Atelectasis present" quoted from *"No focal consolidation, atelectasis, or pneumothorax"* | CheXbert mislabels list negations on the full report | negation guard + quote must agree with the label (G9) |
| 3 | confidence 1.00 on a report with one finding | support-only average | shrink toward 0.5 by evidence coverage |
| 4 | first report attempt died with a `charmap` error | TorchXRayVision progress bar writes `█` to a cp1252 console | UTF-8 stdout + pre-downloaded weights |
| 5 | `chex`/`mimic_ch` checkpoints refused to load | those heads return blank names | guard accepts named subsets, still refuses unknown names |

After the fixes the same report yields 8 findings with correct polarity, and the
UI highlights *"No focal consolidation, atelectasis, or pneumothorax"* as
**absent/supported** rather than as a positive claim.

## 4. Verifier gate — the important result

500 OpenI studies, CheXbert on the reference report as truth, youden threshold.

| Finding | pos/500 | AUC (all) | AUC (chex) | AUC (mimic_ch) | usable |
|---|---|---|---|---|---|
| Pleural Effusion | 18 | **0.822** | 0.776 | **0.826** | **yes** |
| Cardiomegaly | 78 | 0.744 | 0.623 | 0.610 | no |
| Atelectasis | 30 | 0.710 | 0.599 | 0.674 | no |
| Consolidation | 10 | 0.666 | 0.609 | 0.619 | no |
| Pneumonia | 6 | 0.636 | 0.610 | 0.711 | no |
| Lung Opacity | 87 | 0.573 | 0.586 | 0.601 | no |
| Enlarged Cardiomediastinum | 19 | 0.554 | 0.614 | 0.622 | no |
| Fracture | 10 | 0.539 | 0.416 | 0.399 | no |
| Lung Lesion | 22 | 0.533 | 0.478 | 0.466 | no |
| Pleural Other | 7 | 0.574 | — | — | no |

**Conclusion: DenseNet-121 cannot verify more than pleural effusion on this
corpus.** Three pretrained weight sets agree on that.

Two caveats that cut against the classifier and are worth stating in the report:

* our 500-study set contains **lateral views** (square images passed the frontal
  filter); a lateral image has no meaningful "cardiomegaly" probability;
* the reference labels come from **terse OpenI reports** (effusion prevalence
  3.6 %, far below a real chest-radiograph population), so a correct image model
  is scored as a false positive.

Both mean the AUCs above are a **lower bound**, not the model's ceiling.

## 5. Decision taken

The system now gates assessability on the measured AUC (`MIN_AUC = 0.75`):

* Pleural Effusion → verified;
* every other finding → `not assessable`, shown grey in the UI and never counted
  as correct.

This is deliberately smaller than the report's promise and larger than nothing:
one finding is verified with real evidence, and the system says so instead of
pretending.

## 6. Still open

| Item | Status |
|---|---|
| Finding-level risk–coverage on the generated reports | running (`trustmed/eval/verifier_value.py`) |
| Lateral-view filter for the 500 set | not done; would raise every AUC |
| Second image model (BiomedCLIP zero-shot) | not tried; only remaining path to verifying more findings |
| Reader study | not started |
