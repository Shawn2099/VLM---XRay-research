# MedGemma 1.5 4B backend

Second backend for the same chest-X-ray service. It uses Google's
[`google/medgemma-1.5-4b-it`](https://huggingface.co/google/medgemma-1.5-4b-it)
(Gemma 3 4B medical multimodal, 4.3B params, bf16, 8.6 GB) instead of
ECOFRI/CXR-LLAVA-v2.

The API, UI and API key are identical. **Only one model runs at a time** — both
need most of the 24 GB vGPU — so switching is a one-command operation on port
8000.

## Switch

```powershell
.\medgemma\switch.ps1 -Model medgemma   # MedGemma 1.5 4B
.\medgemma\switch.ps1 -Model cxr        # CXR-LLaVA v2
```

Both answer at <http://10.10.10.28:8000/> with the same key
(`/home/iccc/cxr-llava/deploy/api.key`) and the same UI.

## Build / upload

```powershell
.\medgemma\push.ps1                 # code + wheels + 8.1 GiB model
ssh icccserver 'bash /home/iccc/medgemma/deploy/build_and_run.sh'
.\medgemma\switch.ps1 -Model medgemma
```

The image is built offline on `transformers 5.14.1` with the working
JupyterLab stack (torch 2.5.0+cu121). The CXR-LLaVA image stays on
`transformers 4.36.2` and is untouched.

## Test

```powershell
# the normal harness, pointed at whichever backend is active
python test\evaluate_api.py --api-key <KEY> --temperature 0 --limit 120
python test\evaluate_api.py --api-key <KEY> --temperature 0 --frontal-only --out test\results\medgemma_frontal
python test\qa_test.py --api-key <KEY> --limit 50
python test\edge_cases.py --api-key <KEY>
```

The DICOM/HTTP code is a copy of the CXR-LLaVA service, so the 49/49 + 58/58
edge suites should pass unchanged.

## Status (2026-11-14)

| Item | State |
|---|---|
| Model download | complete, 15 files, 8.05 GiB, index/headers verified |
| `medgemma:1.0` image | builds offline; dedicated venv |
| Model load | OK, 8.02 GiB VRAM |
| Inference | **working** — sample report 5.46 s, QA 4.09 s |
| Active backend | **MedGemma 1.5 4B**; switch back with `-Model cxr` |

### Benchmark vs CXR-LLaVA (same 120 OpenI images, greedy)

| Metric | CXR-LLaVA v1.5 | MedGemma 1.5 4B |
|---|---|---|
| Latency | **2.01 s** | 3.57 s |
| Unigram F1 | 0.209 | **0.275** |
| Finding macro F1 | 0.150 | **0.228** |
| Micro precision / recall | 0.207 / 0.315 | **0.467 / 0.583** |
| Frontal subset F1 | 0.096 | **0.164** |
| QA accuracy (100) | **0.90** | 0.71 |
| Cardiomegaly yes/no | 1/4 found, 0 false positives | **4/4 found**, 20 false positives |
| Edge/DICOM | 49/49 + 58/58 | 49/49 + 58/58 |
| VRAM | 13.2 GiB | **8.0 GiB** |
| Output | paragraph | **Findings + Impression** |

MedGemma is the better report-quality backend and is the current default;
CXR-LLaVA is faster and far more conservative on yes/no questions. Neither is
clinically usable — both are research/demo models.

### 500-study results

| Metric | CXR-LLaVA | MedGemma |
|---|---|---|
| Latency | **1.96 s** | 3.61 s |
| Keyword macro F1 | 0.118 | **0.186** |
| Keyword unigram F1 | 0.214 | **0.276** |
| CheXbert micro/macro | 0.214 / 0.135 | **0.251 / 0.161** |
| RadGraph RG_ER | 0.226 | **0.293** |
| BLEU-4 / ROUGE-L | 3.56 / 0.208 | **4.49 / 0.216** |
| Balanced QA cardiomegaly sens/spec | 0.100 / 0.967 | **0.867** / 0.600 |
| Balanced QA effusion sens/spec | 0.000 / 1.000 | **0.538** / 0.885 |

Paired macro difference: **+0.066 [0.010, 0.121], p = 0.012**. Disagreement:
81.3 % of finding rows agree with 4.6 % both-wrong; MedGemma correct on 639 of
936 disagreements vs 297 for CXR-LLaVA.

### Stack choice

`transformers 4.57.1` and `5.14.1` both build Gemma 3 masks with helpers that
require **torch >= 2.6**; the host has torch 2.5.0+cu121. Rather than pull a
~3 GB torch/CUDA upgrade, the image uses a **dedicated venv** with
`transformers 4.51.3` + `tokenizers 0.21.4`, whose Gemma 3 code still uses the
older `_update_causal_mask` and works on torch 2.5. CXR-LLaVA keeps its own
`transformers 4.36.2` environment — the two never share packages.

The torch 2.6.0+cu124 wheels are downloaded in `wheels_torch/` as a fallback,
but are not needed with 4.51.3.

## Licence

MedGemma 1.5 is gated under Google's **Health AI Developer Foundations
(HAI-DEF)** terms, not an open-source licence. It is research/validation-only;
clinical use requires separate validation and regulatory clearance. Do not
redistribute the weights outside the terms.

## Model files

`../medgemma-1.5-4b-it/` (8.05 GiB, 15 files, 2 safetensors shards). Verified
with `python medgemma/verify_model.py`.
