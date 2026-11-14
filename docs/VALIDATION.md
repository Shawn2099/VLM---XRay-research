# TrustMed — end-to-end validation

Run on this machine against the live services, 2026-11-15. Nothing below is
projected; where a number is missing it says so.

## 1. What is running

| Piece | Where | State |
|---|---|---|
| Report service | `10.10.10.28:8000` (MedGemma 1.5 4B) | healthy, 8.0 GiB VRAM |
| TrustMed | `127.0.0.1:8010`, FastAPI + Jinja, CPU | healthy |
| Store | `data_trustmed/trustmed.db` (SQLite, WAL) | 8 tables |
| Verifier | CheXbert 0.0.2 + DenseNet-121 ensemble (3 checkpoints), CPU | loaded |
| Calibration | `data_trustmed/calibration.json` from 500 OpenI studies | applied |

## 2. Functional tests

| Suite | Result |
|---|---|
| `test/trustmed_e2e.py` | **29 / 29** |
| `test/trustmed_ingest.py` | **6 / 6** |

Covered: login, wrong password, unauthenticated upload, upload, DICOM ingest,
16-bit PNG refusal, colour-photo refusal, garbage refusal, hash dedupe, report
generation, findings, confidence in range, valid status, read-back, review,
invalid review action, history, CheXbert self-test, classifier label map.

End-to-end latency: **3.9 – 4.8 s** (generation ≈ 3.6 s on the remote GPU,
CheXbert ≈ 0.35 s, DenseNet ensemble ≈ 0.35 s).

## 3. Bugs the tests found, and the fix

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | only 2 findings per report | CheXbert returns **0 for "absent"**; code treated 0 as "not mentioned" | `1→present`, `0→absent`, `−1→hedged`, `''→not mentioned` |
| 2 | "Atelectasis present" quoted from *"No focal consolidation, atelectasis, or pneumothorax"* | CheXbert mislabels list negations | negation guard + quote must agree with its label |
| 3 | confidence 1.00 on a one-finding report | support-only average | shrink toward 0.5 by evidence coverage |
| 4 | `charmap` crash on first model load | progress bar writes `█` to cp1252 | UTF-8 stdout + pre-downloaded weights |
| 5 | `chex` / `mimic_ch` refused to load | their heads return blank names | guard accepts named subsets, still refuses unknown names |
| 6 | contradictions were 97 % false alarms | Youden thresholds on 3.6 % prevalence | two operating points at 95 % sens / 95 % spec |
| 7 | `NameError: ingest` on first report | missing import | added |
| 8 | lateral views were "verified" | no view check | symmetry check; lateral ⇒ verification disabled |

## 4. Verifier gate — 500 OpenI studies

CheXbert on the reference report is treated as truth. Ensemble = mean of the
`all`, `chex` and `mimic_ch` DenseNet-121 checkpoints.

| Finding | pos/500 | AUC | thr (95 % spec) | PPV at thr | tier |
|---|---|---|---|---|---|
| Pleural Effusion | 18 | **0.850** | 0.76 | 0.31 | **verified** |
| Cardiomegaly | 78 | 0.694 | 0.66 | 0.46 | advisory |
| Atelectasis | 30 | 0.683 | 0.73 | 0.27 | advisory |
| Pneumonia | 6 | 0.655 | 0.64 | 0.00 | not assessable (PPV) |
| Consolidation | 10 | 0.639 | 0.70 | 0.09 | not assessable |
| Enlarged Cardiomediastinum | 19 | 0.633 | 0.65 | 0.12 | not assessable |
| Lung Opacity | 87 | 0.596 | 0.84 | 0.30 | not assessable |
| Pleural Other | 7 | 0.574 | — | — | not assessable |
| Lung Lesion | 22 | 0.511 | — | — | not assessable |
| Fracture | 10 | 0.419 | — | — | not assessable |
| Edema / Pneumothorax | 4 / 2 | — | — | — | too few positives |

Ensemble beats every single checkpoint (effusion 0.822 / 0.776 / 0.826 → 0.850).

## 5. The lateral-view result (most important)

Half of the "frontal" 500-set is not frontal: the builder accepted square images.
Mirror-symmetry cleanly separates them (lateral 0019 = 0.15, frontal 0200 = 0.95).
Recomputing AUC on progressively more symmetric subsets, no model re-run:

| Finding | all 500 | sym>0.4 (309) | sym>0.55 (251) | sym>0.7 (182) |
|---|---|---|---|---|
| Pleural Effusion | 0.850 | **0.916** | 0.925 | — |
| Pneumonia | 0.655 | **0.857** | 0.898 | — |
| Atelectasis | 0.683 | 0.728 | **0.797** | 0.828 |
| Cardiomegaly | 0.694 | 0.740 | 0.757 | **0.775** |
| Enlarged Cardiomediastinum | 0.633 | 0.745 | 0.728 | 0.780 |
| Lung Opacity | 0.596 | 0.642 | 0.677 | 0.705 |

So most of the gate failure was a **data** problem, not only a model problem.
Caveat, stated rather than hidden: selecting on symmetry preferentially removes
abnormal images (large effusions are asymmetric), so these subset AUCs are
optimistic and are *not* used for the shipping calibration.

## 6. What the system does now

* **Pleural Effusion** — full verdicts (supported / uncertain / unsupported /
  contradiction).
* **Cardiomegaly, Atelectasis** — advisory only: may flag extreme disagreement,
  never clears a finding (PPV 0.46 and 0.27 make clearing unsafe).
* **Everything else** — `not assessable`, grey, never counted as correct.
* **Lateral / low-symmetry image** — verification disabled, status
  `review_required`, reason shown in the UI.
* **Auto-accept** requires ≥ 3 independently verifiable findings; the current
  gate never reaches that, so every report is routed to review. That is the
  honest state, not a bug.

## 7. Still open

| Item | Status |
|---|---|
| Rebuild the 500-set frontal-only and re-run both models | not done (≈ 1 h GPU + metrics) |
| Verifier-value analysis on generated reports | script ready, needs a run after the rebuild |
| Reader study | not started |
| Second image model (BiomedCLIP zero-shot) | untried; only remaining route to widening the verified set |
