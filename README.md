# Chest X-ray report service — CXR-LLaVA v2 + MedGemma 1.5 4B

Chest X-ray report generation with two switchable backends on `icccserver`
(NVIDIA L40S-24Q): **ECOFRI/CXR-LLAVA-v2** and **Google MedGemma 1.5 4B**.
Both expose the same browser UI, HTTP API and API key; only one runs at a time
because both need most of the 24 GB vGPU.

**Research use only. Both models can be wrong and must not be used for clinical
decisions.** CXR-LLaVA is CC-BY-NC-4.0 plus Meta Llama-2; MedGemma is gated
under Google's HAI-DEF terms.

## Use it

Active backend: **MedGemma 1.5 4B** (switch anytime):

```powershell
.\medgemma\switch.ps1 -Model medgemma
.\medgemma\switch.ps1 -Model cxr
```

Open <http://10.10.10.28:8000/> and paste the API key. The key is stored on the
server at `/home/iccc/cxr-llava/deploy/api.key` (printed once by the build).

Workstation-only access (no LAN): run `.\deploy\tunnel.ps1` and open
<http://127.0.0.1:8010/>.

API (multipart `file` = DICOM/PNG/JPEG):

```bash
curl -X POST http://10.10.10.28:8000/report \
  -H "X-API-Key: $CXR_API_KEY" \
  -F "file=@cxr.dcm" -F "temperature=0.2" -F "top_p=0.8"

curl -X POST http://10.10.10.28:8000/ask \
  -H "X-API-Key: $CXR_API_KEY" \
  -F "file=@cxr.jpg" -F "question=Is there cardiomegaly?"
```

Endpoints: `GET /health`, `GET /config`, `POST /preview`, `POST /report`,
`POST /differential`, `POST /ask`.

## How it runs

```
browser / app ──HTTP──► uvicorn :8000 (X-API-Key)
                        ├─ cxr-llava:1.5   (13.2 GiB, transformers 4.36.2)
                        │    └─ /models/cxr-llava
                        └─ medgemma:1.0    (8.0 GiB, venv + transformers 4.51.3)
                             └─ /models/medgemma-1.5-4b-it
```

* only one backend container runs at a time; `switch.sh` stops both and starts
  the chosen one on the same host port
* each backend has its own image and Python environment — no shared packages
* one request at a time per backend; the model is serialised with a lock
* DICOM is windowed to 8-bit here; multi-frame and colour DICOM are rejected
  with a clear error
* model directories mounted read-only; `cap-drop ALL`, `no-new-privileges`,
  2 GiB tmpfs `/tmp`
* CXR-LLaVA loads in ~14 s; MedGemma loads in ~40 s

Deployment details and runbook: [`deploy/PLAN.md`](deploy/PLAN.md).

## Repository layout

| path | contents |
|---|---|
| `model/` | the 15 verified CXR-LLaVA files (13.1 GiB, safetensors) |
| `medgemma-1.5-4b-it/` | the verified MedGemma model (8.05 GiB) |
| `deploy/` | CXR-LLaVA FastAPI app, UI, Dockerfile, build/push scripts |
| `medgemma/` | MedGemma service, venv image, switch/upload scripts |
| `deploy/wheels/` | offline CXR-LLaVA wheels |
| `medgemma/wheels/` | offline MedGemma venv wheels |
| `test/` | OpenI subset, edge/QA/concurrency/evaluation/compare harnesses |
| `TEST_REPORT.md` | full test results, backend comparison, residual risks |
| `icccserver-IR-*/` | unrelated incident-response evidence for the host |

## Tests

```powershell
.\test\run_all.ps1 -ApiKey <KEY>
```

Latest results (2026-11-14):

| Metric | CXR-LLaVA v1.5 | MedGemma 1.5 4B |
|---|---|---|
| OpenI 500 studies | 500/500, **1.96 s** | 500/500, 3.61 s |
| Keyword macro F1 | 0.118 | **0.186** |
| Keyword unigram F1 | 0.214 | **0.276** |
| Paired macro difference | — | +0.066 [0.010, 0.121], p=0.012 |
| Balanced QA, cardiomegaly sens/spec | 0.100 / 0.967 | **0.867** / 0.600 |
| Balanced QA, effusion sens/spec | 0.000 / 1.000 | **0.538** / 0.885 |
| Edge/DICOM checks | 49/49 + 58/58 | 49/49 + 58/58 |
| VRAM | 13.2 GiB | **8.0 GiB** |

MedGemma is the better report generator and the current default; CXR-LLaVA is
faster and extremely conservative on yes/no questions. Neither is clinically
accurate. See `TEST_REPORT.md`, `paper/TABLES.md` and `test/results/compare.md`.

Dataset: OpenI / Indiana University CXR via the public HF mirror
`Shrey-1329/cxiu_hf_dataset`; research use only.

## Paper

The paper-grade protocol is in [`PAPER_PROTOCOL.md`](PAPER_PROTOCOL.md):
500-study OpenI test set, CheXbert/RadGraph + text metrics, balanced QA,
bootstrap CIs, disagreement analysis, and a reader-study plan. The 120-image
results in `TEST_REPORT.md` are the pilot; the 500-study run replaces them.
A section-by-section draft skeleton is in [`paper/DRAFT.md`](paper/DRAFT.md).

## Known limits

* plain HTTP on the LAN — put TLS in front before real use
* no PHI de-identification; the service stores nothing but does not clean tags
* lateral views and multi-frame studies are out of scope
* model accuracy is not sufficient for clinical use
