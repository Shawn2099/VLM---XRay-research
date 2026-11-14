# TrustMed

Chest X-ray report generation with **finding-level verification** and a
**calibrated confidence score**. Research prototype — not a diagnostic device.

```
upload ─▶ CXR-LLaVA / MedGemma (GPU, :8000) ─▶ report text
                                                     │
      ┌───────────────────────────────────────────────┤
      ▼                                               ▼
DenseNet-121 (image → 12 probs)              CheXbert (report → 14 labels + sentence)
      └──────────────────┬────────────────────────────┘
                         ▼
                 verdict engine  (supported · uncertain · unsupported ·
                                  contradiction · omission · not assessable)
                         ▼
                 confidence (severity-weighted, isotonic-calibrated)
                         ▼
                 SQLite ─▶ UI ─▶ radiologist review ─▶ audit log
```

## Run

```powershell
# 1. the report service must already be up (either backend)
.\medgemma\switch.ps1 -Model medgemma      # or -Model cxr

# 2. TrustMed
.\trustmed\run.ps1                         # http://127.0.0.1:8010
.\trustmed\run.ps1 -Name cxr               # same, labelled for CXR-LLaVA
```

Equivalent manual start:

```powershell
$env:PYTHONPATH="."
$env:TRUSTMED_API_KEY="<key from deploy/api.key>"
$env:TRUSTMED_BACKEND_NAME="medgemma"
metrics-venv\Scripts\python -m uvicorn trustmed.main:app --port 8010
```

Open <http://127.0.0.1:8010>. Default account: `admin@trustmed.local` /
`trustmed-admin` — **change it** with `TRUSTMED_ADMIN_PASSWORD` before showing
anyone.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `TRUSTMED_BACKEND` | `http://10.10.10.28:8000` | report service base URL |
| `TRUSTMED_API_KEY` | `deploy/api.key` | key for that service |
| `TRUSTMED_BACKEND_NAME` | `cxr-llava` | label shown in the UI |
| `TRUSTMED_DATA` | `./data_trustmed` | SQLite, images, calibration |
| `TRUSTMED_SECRET` | dev value | session signing key |
| `TRUSTMED_ADMIN_EMAIL` / `_PASSWORD` | see `config.py` | seeded admin |
| `TRUSTMED_POS` / `_UNCERTAIN` | 0.70 / 0.30 | verdict thresholds (overridden per finding by calibration) |
| `TRUSTMED_OMISSION` / `_OMISSION_PPV` | 0.90 / 0.50 | omission guardrail |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | service, backend and label-map check |
| GET | `/api/selftest` | CheXbert + DenseNet guardrails |
| POST | `/api/upload` | store image, return `image_id` |
| POST | `/api/report` | run the pipeline, persist, return findings + confidence |
| GET | `/api/reports/{id}` | read back |
| POST | `/api/findings/{id}/review` | radiologist accept / edit / reject |
| GET | `/history` | worklist |

## Guardrails in code

1. **Label map asserted at load** — TorchXRayVision's 18 heads are mapped
   explicitly to CheXbert's 14; a change raises instead of guessing.
2. **Four label states kept** — `+1 / −1 / not mentioned`, never collapsed
   before the verdict engine.
3. **Negation correction** — if every mention of a positive label is negated
   ("no consolidation, atelectasis, or pneumothorax"), polarity flips; the reason
   string says so.
4. **Quotes must agree** — a finding's quoted sentence must itself be labelled
   the same way; otherwise no quote is shown.
5. **Omission needs high precision** — only at p ≥ 0.90 *and* per-finding PPV ≥ 0.50.
6. **Short reports never auto-pass** — fewer than 3 verifiable findings is at
   most "review suggested".
7. **Calibrated thresholds** — `trustmed/eval/verify_gate.py` writes per-finding
   thresholds from the 500-study run; the verdict engine reads them.

## Known limits

* Agreement is a **second opinion**, not ground truth: CheXbert and DenseNet both
  descend from the CheXpert ontology, so their errors correlate.
* Only the findings the image model actually predicts are verifiable
  (`Support Devices` and `No Finding` are always "not assessable").
* Zero-shot on OpenI; no clinical validation; no reader study yet.
* CheXbert weights are Stanford academic / non-commercial.
