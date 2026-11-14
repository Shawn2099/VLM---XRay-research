# CXR-LLaVA + MedGemma deployment — test report

Date: 2026-11-14  
Services: `cxr-llava:1.5` and `medgemma:1.0` on `icccserver` (10.10.10.28),
NVIDIA L40S-24Q  
Stacks: CXR-LLaVA `transformers 4.36.2` / torch 2.5; MedGemma venv
`transformers 4.51.3` / torch 2.5

Verdict: **engineering is ready for research/demo use; neither model is
clinically accurate.** All transport, format, auth, DICOM, UI and failure paths
pass for both backends. Current default: **MedGemma 1.5 4B**; CXR-LLaVA is one
switch away.

---

## 1. What was tested

| Area | Coverage |
|---|---|
| Report generation | 120 OpenI images + full FINDINGS text per backend; 74 frontal subset; 30-image `temperature=0.2` CXR run |
| Other endpoints | `/preview`, `/differential`, `/ask`, `/config`, `/health`, `/` |
| Determinism | same image, `temperature=0`, twice |
| Question answering | 50 images × 2 yes/no questions; 5 definitional questions |
| Concurrency | 3 simultaneous report requests |
| Images | PNG (L/RGBA/palette), JPEG, EXIF-rotated JPEG, 16-bit PNG, 64 MP PNG, tiny 8×8, corrupt, empty, 45 MB body |
| DICOM | uncompressed 8/12/16-bit, signed pixels, MONOCHROME1/2, VOI window, no window, zero window, modality LUT, VOI LUT sequence, no preamble, missing PixelData/Rows, colour 3/4-byte, multi-frame, JPEG 2000 lossless, JPEG lossless, JPEG-LS, RLE |
| Security | auth missing/wrong, header injection, key permissions, container caps/mounts, logs, `/docs` |
| UI | no-key 401 path, DICOM upload, preview chips, report, copy over HTTP, invalid sampling values, landscape warning |
| Operations | container restart, health, VRAM, request logs, tmpfs contents |

Datasets:

* **OpenI / Indiana University CXR**, 120 image/report pairs, fetched from the
  public HF mirror `Shrey-1329/cxiu_hf_dataset` (the NLM Open-i site was under
  maintenance). 22 MB; 46 landscape (likely lateral), 44 portrait, 30 square.
* **pydicom-data** files for compressed/multi-frame transfer syntaxes.
* Synthetic 12-bit DICOMs generated from the CC0 sample.

---

## 2. Results

### 2.1 Transport, formats, security

| Suite | Result |
|---|---|
| Main edge suite (`test/edge_cases.py --dicom-dir test/data/dicom`) | **49/49 pass** |
| Extra DICOM/HTTP suite (`--dicom-dir test/data/dicom/extra`) | **58/58 pass** |
| No-key / wrong-key | 401 |
| 45 MB body | 413 before buffering |
| 16-bit PNG | 422 with a DICOM hint |
| Multi-frame / colour / 32-bit DICOM | 422 |
| Missing preamble DICOM | 200 (force fallback works) |
| Header injection via `Modality` | blocked: `X-Evil` absent, value sanitised to `CRX-Evil injected` |
| EXIF orientation 6 | 320×160 JPEG returned as 160×320 |
| `/docs`, `/openapi.json` | 404 (disabled) |
| CORS preflight | 200, `access-control-allow-origin: *` |
| GET `/report` / unknown route | 405 / 404 |
| JPEG 2000, JPEG lossless, JPEG-LS | decoded 200, non-blank previews |
| MONOCHROME1 vs MONOCHROME2 (inverted input) | byte-identical preview PNGs |
| Windowed vs 1–99 percentile no-window | byte-identical preview PNGs |
| DICOM `signed`, `zerowindow`, `nopreamble` | 200, non-blank |
| DICOM 8-bit, modality LUT, VOI LUT sequence | 200, non-blank (added to the extra suite) |
| `nopixels`, `norows` | 422 |

### 2.2 Report generation — all 120 images

| Metric | Value |
|---|---|
| Success | **120/120** (0 errors, 0 empty) |
| Latency | mean **2.01 s**, median 1.94 s, p95 3.04 s, max 3.83 s |
| Report length | 36.5 words mean (18–72) |
| Repetition (8-gram) | **0.000** mean/max |
| Unique reports | 109/120 (11 duplicates — mostly normal templates) |
| Truncated / prompt artefacts | 0 / 0 |
| Unigram F1 vs reference | 0.209 |
| Finding macro F1 | 0.150 (micro P 0.207 / R 0.315) |

Finding detail (all views):

| finding | ref+ | model+ | TP | FP | FN | F1 |
|---|---|---|---|---|---|---|
| atelectasis | 13 | 23 | 4 | 19 | 9 | 0.222 |
| cardiomegaly | 12 | 37 | 10 | 27 | 2 | 0.408 |
| consolidation | 1 | 16 | 1 | 15 | 0 | 0.118 |
| edema | 1 | 11 | 0 | 11 | 1 | 0.000 |
| effusion | 7 | 19 | 0 | 19 | 7 | 0.000 |
| pneumonia | 2 | 18 | 1 | 17 | 1 | 0.100 |
| pneumothorax | 4 | 4 | 0 | 4 | 4 | 0.000 |
| nodule/mass | 2 | 5 | 1 | 4 | 1 | 0.286 |
| fracture | 4 | 0 | 0 | 0 | 4 | 0.000 |
| normal | 62 | 31 | 17 | 14 | 45 | 0.366 |

The model **over-calls** cardiomegaly, effusion, edema, atelectasis and
pneumonia on OpenI, and rarely states "normal" when the reference does.

### 2.3 Frontal/square subset (74 images; laterals out of scope)

* 74/74 success, mean **2.07 s**, 37.4 words, 71/74 unique, 0 repetition
* unigram F1 0.209; finding macro F1 **0.096** (micro P 0.154 / R 0.250)
* over-calling remains: cardiomegaly 22 predicted vs 4 reference, effusion
  12 vs 3, edema 8 vs 0

### 2.4 Sampling variance — 30 images at `temperature=0.2`, `top_p=1.0`

* 30/30 success, mean **1.99 s**, max 2.88 s
* 36.0 words, 28/30 unique, repetition 0.000
* unigram F1 0.197; macro F1 0.083 — effectively the same as greedy

### 2.5 Question answering

**CXR-LLaVA v1.5** (100 questions):

| Question | n | Accuracy | TP | FN | TN | FP | Unknown |
|---|---|---|---|---|---|---|---|
| Is there cardiomegaly? | 50 | 0.94 | 1 | 3 | 46 | 0 | 0 |
| Is there a pleural effusion? | 50 | 0.86 | 0 | 6 | 43 | 1 | 1 |
| **Overall** | **100** | **0.90** | | | | | **1** |

**MedGemma 1.5 4B** (same 100 questions):

| Question | n | Accuracy | TP | FN | TN | FP | Unknown |
|---|---|---|---|---|---|---|---|
| Is there cardiomegaly? | 50 | 0.60 | **4** | 0 | 26 | **20** | 0 |
| Is there a pleural effusion? | 50 | 0.82 | 2 | 4 | 39 | 5 | 0 |
| **Overall** | **100** | **0.71** | | | | | **0** |

The two fail in opposite directions. CXR-LLaVA is conservative: it finds only
**1/4 cardiomegaly** and **0/6 effusion** positives but almost never raises a
false alarm. MedGemma finds **all 4 cardiomegaly** positives but over-calls
**20/46 negatives**. Raw accuracy hides this because 90–92 % of the questions
are negative. Five definitional questions ("What is consolidation?") were
answered coherently by both.

### 2.6 Differential diagnosis, determinism, concurrency, restart

| Check | Result |
|---|---|
| `/differential`, 20 images | 20/20, mean 1.26 s, 17/20 unique |
| Determinism, 5 images × 2 at `temperature=0` | **5/5 identical** |
| Concurrency, 3 simultaneous reports | all 200; wall 4.55 s; `/health` OK; VRAM unchanged |
| UI | report, DICOM upload, Ask (`0.66 s`, "No, there is no evidence of cardiomegaly."), copy over HTTP, validation, landscape warning all work |
| Container restart | healthy in **14 s**, report succeeded |
| VRAM | 13.19 GiB allocated / 13.22 reserved; GPU total 15.6/24.6 GB |
| Container `/tmp` after all tests | 76 KB (HF modules only; no images stored) |
| Logs | no traceback, no API key, no uploaded filename |
| Container security | `cap-drop ALL`, `no-new-privileges`, model mount `rw=false`, `/tmp` tmpfs 2 GiB |
| Key file | `-rw-------` 49 bytes (48 hex chars = 192 bits) |

**MedGemma 1.5 4B equivalents:**

| Check | MedGemma result |
|---|---|
| Edge/DICOM suites | **49/49 + 58/58 pass** (same code, all formats/transfer syntaxes) |
| `/differential`, 20 images | 20/20, mean **10.82 s**, 20/20 unique |
| Determinism, 5 × 2 at `temperature=0` | **5/5 identical** |
| Concurrency, 3 simultaneous reports | all 200; wall 10.73 s; `/health` OK |
| UI | report in **4.33 s**, structured Findings/Impression, title "MedGemma 1.5 4B" |
| VRAM | **8.02 GiB** allocated / 8.04 reserved |
| Container | venv uvicorn, healthcheck `healthy`, same port/UI/key |

### 2.7 Backend comparison — CXR-LLaVA v1.5 vs MedGemma 1.5 4B

Same 120 OpenI images, `temperature=0`, greedy, same API/UI/key.

| Metric | CXR-LLaVA v1.5 | MedGemma 1.5 4B |
|---|---|---|
| Success | 120/120 | 120/120 |
| Latency mean / p95 / max | **2.01 s / 3.04 s / 3.83 s** | 3.57 s / 4.54 s / 5.14 s |
| Report length | 36.5 words | 45.5 words |
| Repetition (8-gram) | **0.000** | 0.0008 |
| Unigram F1 | 0.209 | **0.275** |
| Finding macro F1 | 0.150 | **0.228** |
| Finding micro P / R | 0.207 / 0.315 | **0.467 / 0.583** |
| Frontal subset, 74 images | 0.096 macro / 0.209 unigram | **0.164 macro / 0.277 unigram** |
| CheXbert micro F1 / macro F1 (120) | 0.256 / 0.143 | **0.355 / 0.194** |
| RadGraph RG_ER (120) | 0.222 | **0.296** |
| BLEU-4 / ROUGE-L (120) | 3.42 / 0.199 | **4.58 / 0.217** |
| BERTScore F1 (120) | 0.820 | 0.821 (no meaningful difference) |
| QA accuracy, 100 questions | **0.90** | 0.71 |
| Cardiomegaly sensitivity | 1/4 | **4/4** |
| Cardiomegaly false positives | **0/46** | 20/46 |
| `/differential`, 20 images | **1.26 s** mean | 10.82 s mean |
| Edge/DICOM suites | 49/49 + 58/58 | 49/49 + 58/58 |
| VRAM | 13.2 GiB | **8.0 GiB** |
| Structured output | free paragraph | **Findings/Impression sections** |

MedGemma is the better **report-quality** backend (structured output, higher
F1) and is the current default; CXR-LLaVA is ~1.8× faster and much more
conservative on yes/no questions. MedGemma still misses
pneumonia/pneumothorax/fracture in this sample, over-calls cardiomegaly, and
over-calls "normal" (99/120 under our broad keyword label). Neither is
clinically usable. Both are retained; one command switches them.

### 2.8 500-study results (paper-grade set)

The 120-image pilot was optimistic. On the 500 frontal OpenI studies:

| Metric | CXR-LLaVA v1.5 | MedGemma 1.5 4B |
|---|---|---|
| Reports / failures | 500 / 0 | 500 / 0 |
| Latency mean / p95 / max | **1.96 s / 2.88 s / 4.71 s** | 3.61 s / 4.38 s / 6.91 s |
| Report length | 35.8 words | 45.8 words |
| Keyword macro F1 | 0.118 | **0.186** |
| Keyword micro P / R | 0.138 / 0.231 | **0.395 / 0.560** |
| Bootstrap macro F1 | 0.118 [0.086, 0.152] | **0.184 [0.143, 0.229]** |
| Bootstrap unigram F1 | 0.214 [0.205, 0.224] | **0.276 [0.268, 0.284]** |
| Paired macro difference | — | **+0.066 [0.010, 0.121], p = 0.012** |
| Paired unigram difference | — | **+0.062 [0.051, 0.072], p < 0.001** |
| CheXbert micro F1 | 0.214 | **0.251** |
| CheXbert macro F1 | 0.135 | **0.161** |
| CheXbert omission / false-positive | 71.3 % / 11.0 % | **68.5 % / 9.4 %** |
| RadGraph RG_ER | 0.226 | **0.293** |
| BLEU-4 / ROUGE-L | 3.56 / 0.208 | **4.49 / 0.216** |
| BERTScore F1 | 0.822 | 0.820 (tie) |

MedGemma over-calls atelectasis (355 predicted vs 44 reference) and “No
Finding” (292 vs 115), while missing 71/85 cardiomegaly and every
pneumonia/pneumothorax/fracture label. CXR-LLaVA over-calls cardiomegaly
(175 vs 85 CheXbert-positive), effusion (87 vs 22), consolidation (77 vs 12),
edema (56 vs 7) and pneumonia (71 vs 9), while missing most normals (161
predicted vs 115). Both models have very high CheXbert omission rates
(71.3 % CXR, 68.5 % MedGemma), i.e. they fail to state most reference-positive
findings.

**Balanced yes/no QA (500 set; equal positives/negatives):**

| Model | Finding | n | Sensitivity | Specificity | PPV | NPV | Accuracy |
|---|---|---|---|---|---|---|---|
| CXR-LLaVA | Cardiomegaly | 60 | **0.100** | 0.967 | 0.750 | 0.518 | 0.533 |
| CXR-LLaVA | Pleural effusion | 52 | **0.000** | 1.000 | 0.000 | 0.500 | 0.500 |
| MedGemma | Cardiomegaly | 60 | **0.867** | 0.600 | 0.684 | 0.818 | 0.733 |
| MedGemma | Pleural effusion | 52 | **0.538** | 0.885 | 0.824 | 0.657 | 0.712 |

The contrast is stark: CXR-LLaVA is effectively a rule-out model (near-zero
sensitivity, high specificity); MedGemma is a rule-in model (high cardiomegaly
sensitivity, moderate specificity).

**Disagreement / selective prediction (500 studies, 5,000 finding rows):**

* models agree on **4,064 rows (81.3 %)**; both are wrong on **4.6 %**
  (95 % CI 4.0–5.3 %) when they agree;
* on **936 disagreements**, MedGemma is correct **639** times, CXR-LLaVA **297**,
  neither 0;
* overall finding error: CXR **16.5 %**, MedGemma **9.7 %**;
* deferring every disagreement covers 81.3 % of rows at 4.6 % retained error.

**Bootstrap 95 % CIs (1,000 resamples, 120 images):**

| Metric | CXR-LLaVA | MedGemma |
|---|---|---|
| Macro F1 | 0.145 [0.091, 0.205] | 0.216 [0.136, 0.302] |
| Unigram F1 | 0.209 [0.194, 0.225] | 0.275 [0.259, 0.290] |

The macro-F1 **unpaired** intervals overlap, but a **paired bootstrap** on the
same studies gives a difference of **+0.071 [0.003, 0.152], p = 0.044** —
significant but fragile at n=120. Unigram F1 is clearly separated
(+0.065 [0.047, 0.084], p < 0.001). The 500-study run is intended to make the
macro-F1 conclusion robust.

**Disagreement analysis (120 studies, 1,200 finding rows):**

* the models agree on **81.4 %** of finding rows and are both wrong only **5.0 %**
  of the time when they agree;
* on the 223 disagreements, MedGemma is correct **155** times, CXR-LLaVA **68**,
  neither 0;
* deferring every disagreement would retain 81.4 % coverage at 5.0 % error,
  versus 17.0 % (CXR) / 9.8 % (MedGemma) without deferral.

---

## 3. Issues found and fixed

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | critical | Multi-frame DICOM decoded every frame before any size check → multi-GB RAM/OOM | reject `NumberOfFrames != 1`; check `Rows×Columns`, `BitsAllocated` before `pixel_array` |
| 2 | critical | Auth ran after the full multipart body was buffered; unbounded uploads | `require_key` is a FastAPI dependency; `Content-Length` middleware rejects >42 MB; reads capped at limit+1 |
| 3 | high | `voi_applied` was always true, so the percentile fallback was dead code | decide from `VOILUTSequence`/`WindowCenter`+`WindowWidth`, require `Width > 0` |
| 4 | high | `.dcm` without preamble never got `force=True` | fallback to forced parse, then return the original error |
| 5 | high | DICOM tag values reflected into response headers → CRLF injection | `_safe_header()` whitelist + truncation; added injection test |
| 6 | medium | API-key comparison not constant-time | `hmac.compare_digest` |
| 7 | medium | Empty model output returned `200` with blank text | `_infer` returns 502 "model produced an empty response" |
| 8 | medium | Phone/camera EXIF orientation ignored; my first fix decoded before the pixel-count guard | `exif_transpose` after a dimensions check, then `load()`; tested 320×160 → 160×320 and 64 MP → 413 |
| 9 | medium | LAN exposure possible without a key | `build_and_run.sh` refuses non-loopback bind without `CXR_API_KEY` |
| 10 | medium | Ctrl+Enter bypassed the busy guard; double submits | guard on `run.disabled` at the top of `runModel` |
| 11 | medium | FastAPI 422 detail rendered as `[object Object]` | `errorText()` flattens validation arrays |
| 12 | medium | Copy silently failed over plain HTTP | `navigator.clipboard` + `execCommand` fallback |
| 13 | medium | Dropping a file outside the drop zone navigated away | document-level `dragover`/`drop` preventDefault |
| 14 | medium | Stale `/preview` responses could overwrite a newer preview | monotonic request token |
| 15 | low | UI allowed empty temperature (became 0) and over-limit files | explicit validation + client-side max size |
| 16 | low | `2.61 S` latency due to uppercase panel heading | CSS override |
| 17 | low | No warning for landscape/lateral input | amber "landscape / likely lateral" chip |
| 18 | low | Header injection / unknown routes untested | added to edge suite; `/docs` disabled |
| 19 | low | `smoke_test.py` docstring mentioned image 1.0 | updated through 1.5 |
| 20 | high | MedGemma inference crashed: transformers 4.57/5.14 require torch≥2.6 for Gemma 3 masks, host has 2.5 | dedicated venv with `transformers 4.51.3` (older `_update_causal_mask`) on torch 2.5; torch 2.6 bundle kept as fallback |
| 21 | medium | Processor crashed on a plain-string system message (`TypeError: string indices`) | system content sent as `[{"type":"text", ...}]` |
| 22 | medium | MedGemma image was missing `pydicom`/GDCM | added to its wheel bundle and preflight |
| 23 | medium | Jupyter entrypoint changed `PATH`; venv healthcheck was ambiguous | absolute `/opt/medgemma/venv/bin/uvicorn` and healthcheck paths |
| 24 | medium | QA polarity parser treated any later “no” as negative (“Yes, … no effusion” → No) | opening-polarity parser + `qa_rescore.py`; both stored sets re-scored |

---

## 4. Residual issues (reported, not fixed)

### 4.1 Model quality — the main limitation

* **CXR-LLaVA** over-calls cardiomegaly, effusion, consolidation, edema and
  pneumonia on the 500-study set; keyword macro F1 0.118, CheXbert micro/macro
  0.214/0.135, RadGraph RG_ER 0.226. It is conservative on yes/no: balanced
  cardiomegaly sensitivity 0.100, effusion 0.000.
* **MedGemma 1.5 4B** is better on report quality (keyword macro 0.186, unigram
  0.276, CheXbert micro/macro 0.251/0.161, RadGraph 0.293) and structured
  output, but over-calls atelectasis and “No Finding” and misses 71/85
  cardiomegaly labels. Balanced QA: cardiomegaly 0.867/0.600,
  effusion 0.538/0.885 sensitivity/specificity.
* Both have very high CheXbert omission rates (71.3 % CXR, 68.5 % MedGemma):
  they fail to state most reference-positive findings.
* OpenI is not one of the models' training datasets, and both model cards state
  research-only with possible hallucination. No prompt or threshold change fixes
  this reliably; it needs a different model or fine-tuning.
* Landscape/lateral images are out of scope. The service warns in the UI and
  the model still processes them; the test report separates frontal results.

### 4.2 Engineering residuals

| Issue | Impact | Recommendation |
|---|---|---|
| Plain HTTP on the LAN; API key and images travel unencrypted | key/image sniffing on the LAN | terminate TLS at a reverse proxy (Caddy/nginx) and keep port 8000 on loopback |
| CORS default `*` | any web page can call the API **if it has the key** | set `CXR_CORS_ORIGINS` to the app origin |
| `TextIteratorStreamer` timeout patched to 120 s, but a failed generation thread still holds the model while the lock is released | rare; could corrupt the next request | restart the container on repeated 500s, or move inference to a killable subprocess |
| `/health` proves HTTP/model load, not generation | a wedged generator can look healthy | add a periodic 8×8 inference probe if uptime matters |
| Multi-frame DICOM rejected | multi-frame CR/CT series need prior frame extraction | add a series viewer/selector or extract the PA frame upstream |
| No PHI de-identification | DICOM metadata is not stripped before processing | de-identify upstream; the service stores nothing but does not clean tags |
| API key printed once by `build_and_run.sh` | may land in a CI/terminal log | read `deploy/api.key` instead of printing in production |
| Base image is 3 months old on an offline host | no security updates | rebuild/patch the host image when possible |
| Host compromise risk accepted by the owner | see `deploy/PLAN.md` §9 | keep the key, loopback/TLS and network allowlist in mind |
| MedGemma is pinned to `transformers 4.51.3` (4.57/5.14 need torch ≥ 2.6) | upgrading transformers will require the torch 2.6 bundle | keep the venv; torch 2.6.0+cu124 wheels are in `medgemma/wheels_torch/` |
| MedGemma is gated under Google HAI-DEF terms | not open source; redistribution restricted | review the terms before sharing weights or outputs |
| Only one backend can run on the 24 GB vGPU | switching reloads the model (14–40 s) | use `switch.ps1`; do not try to start both |

### 4.3 Dataset caveats

* The OpenI mirror includes lateral images; the model is trained on frontal
  CXRs. The 74-image frontal subset is the fairer number.
* Finding F1 uses keyword matching with a negation window; it is a screening
  metric, not a clinical NLP evaluation. Reports are terse and often mention a
  finding only implicitly.
* The NLM Open-i download site was under maintenance; data came from a public
  HF mirror. OpenI is research-use only.

---

## 5. Reproduction

```powershell
# choose the active backend (same URL/UI/key)
.\medgemma\switch.ps1 -Model medgemma
.\medgemma\switch.ps1 -Model cxr

# everything for the active backend; results are namespaced by backend
.\test\run_all.ps1 -ApiKey <KEY>

# targeted runs
python test\evaluate_api.py --api-key <KEY> --temperature 0 --out test\results\medgemma_t0
python test\evaluate_api.py --api-key <KEY> --frontal-only --out test\results\medgemma_frontal
python test\qa_test.py --api-key <KEY> --limit 50 --out test\results\medgemma_qa50.json
python test\qa_rescore.py test\results\medgemma_qa50.json
python test\compare_backends.py test\results\report_t0\summary.json test\results\medgemma_t0\summary.json
python test\edge_cases.py --api-key <KEY> --dicom-dir test\data\dicom\extra
python test\endpoint_matrix.py --api-key <KEY>
```

Artifacts:

```
deploy/PLAN.md                         deployment + runbook
medgemma/README.md                     MedGemma service + switch
test/README.md                         test harness guide
test/results/report_t0/                CXR-LLaVA 120-image report + metrics
test/results/report_t0_frontal/        CXR-LLaVA 74-image frontal subset
test/results/report_t02/               CXR-LLaVA temperature 0.2
test/results/medgemma_t0/              MedGemma 120-image report + metrics
test/results/medgemma_frontal/         MedGemma 74-image frontal subset
test/results/medgemma_qa50*.json       MedGemma 100 QA questions (raw + rescored)
test/results/qa50*.json                CXR-LLaVA 100 QA questions (raw + rescored)
test/results/endpoints.json            CXR differential/determinism/definitional
test/results/medgemma_endpoints.json   MedGemma equivalents
test/results/compare.md                backend comparison table
test/results/run.log                   orchestration log
```

The service is at `http://10.10.10.28:8000/`; the active backend is shown by
`GET /config`. The same key works for both:
`/home/iccc/cxr-llava/deploy/api.key` on the server.
