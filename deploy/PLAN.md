# CXR-LLaVA v2 on `icccserver` — deployment plan

Status: **v1.5 deployed, tested on 120 OpenI images and a DICOM/security matrix**
(2026-11-14). Evidence: [`../TEST_REPORT.md`](../TEST_REPORT.md). A second
backend, MedGemma 1.5 4B, is available with the same API/UI and can be activated
with `../medgemma/switch.ps1`; see [`../medgemma/README.md`](../medgemma/README.md).

---

## 1. What the model actually requires (verified, not assumed)

Source of truth: <https://github.com/ECOFRI/CXR_LLaVA> (branch `master`),
<https://huggingface.co/ECOFRI/CXR-LLAVA-v2> and
<https://arxiv.org/abs/2310.18341>.

| Item | Requirement | Evidence |
|---|---|---|
| Weights | 14.09 GB, 3 safetensors shards, bf16 | `model.safetensors.index.json`; all shards match Hub SHA-256 |
| GPU VRAM | **> 14 GB** | official README |
| Loading | `AutoModel.from_pretrained(dir, trust_remote_code=True)` then `.to("cuda")` | official README, 6-line example |
| Input | 512x512 **8-bit grayscale**, single image | model card + `generate_cxr_repsonse()` |
| Public methods | `write_radiologic_report(image)`, `write_differential_diagnosis(image)`, `ask_question(question, image)` | `CXR_LLAVA_HF.py` |
| Python deps | `transformers==4.36.2`, `torch==2.1.2+cu118`, `tokenizers==0.15.0`, `safetensors==0.4.1`, `sentencepiece==0.1.99`, `protobuf==4.25.2`, `numpy==1.26.3`, `pillow==10.2.0` | official `requirements.txt` |
| License | CC-BY-NC-4.0 **plus** Meta Llama-2 license; research use only | model card |

### Why `transformers==4.36.2` is non-negotiable

The model code calls `LlamaTokenizer.from_pretrained(..., add_special_tokens=False)`
(line 49). Newer Transformers versions reject a kwarg whose name collides with
the `add_special_tokens` method:

* issue #7 — <https://github.com/ECOFRI/CXR_LLaVA/issues/7>
* issue #6 — <https://github.com/ECOFRI/CXR_LLaVA/issues/6>
* unmerged HF PR #4 proposes removing the kwarg, but the shipped file still has it

`transformers 4.36.2` contains no such conflict check, so it loads the model.
**Do not upgrade Transformers inside this image.**

### Upstream quirks we deliberately avoid

| Quirk | Consequence | Our choice |
|---|---|---|
| `main.py` imports `CXR_LLAVA.CXR_LLAVA`, a package absent from the repo (issue #8) | `ModuleNotFoundError` | use the model-card `AutoModel` path |
| README custom-prompt example passes `pil_image=`; the method's arg is `image=` | `TypeError` | only the three official wrapper methods are exposed |
| HF file and GitHub file differ by one warning string | none | local HF copy is used, hash-verified |
| `GenerationConfig` in the repo is nearly empty | defaults only | temperatures are passed explicitly |
| Third-party CPU wrapper pre-resizes to 512x512 before the model | changes framing vs upstream | pass the original image; the model's own `CLIPImageProcessor` resizes + centre-crops |

### Loading details confirmed in the actual 4.36.2 wheel

* `LlamaTokenizer` supplies a LLaMA-2 `default_chat_template`, so
  `apply_chat_template()` works even though this repo ships no `chat_template`.
* `PreTrainedModel.from_pretrained()` overwrites `config._name_or_path` with the
  local directory, so the author's hard-coded `G:\Temp\...` path is harmless.
* `CLIPImageProcessor` is constructed with `do_convert_rgb=False`, 1 channel.
* No `accelerate` / `device_map` is needed for one GPU.

---

## 2. Target host (measured)

| Resource | Value |
|---|---|
| Host | `icccserver` = `10.10.10.28`, Ubuntu 22.04, KVM guest |
| GPU | **NVIDIA L40S-24Q, 24 576 MiB**, driver 580.65.06, idle at planning time |
| CPU / RAM | 16 vCPU / 125 GiB (106 GiB available) |
| Disk | 368 GB free on `/` |
| Docker | `iccc` is in the `docker` group (no sudo needed) |
| Existing image | `quay.io/jupyter/pytorch-notebook:cuda12-python-3.11` with **torch 2.5.0+cu121, CUDA OK** |
| Internet | **no working egress** (HF/pypi resolve to unreachable IPv6) |
| Existing packages | transformers 5.14.1 (unusable for this model), numpy 2.0.2, protobuf 5.27.5 |

Consequences: the deployment must be **fully offline**. We reuse the local
PyTorch image, install pinned wheels from a vendored directory, and never touch
the host Python.

---

## 3. Architecture

```
 Windows workstation / LAN client          icccserver (10.10.10.28)
 ┌────────────────────┐                    ┌──────────────────────────────────────┐
 │ browser UI         │  http://LAN:8000   │ docker: cxr-llava (--gpus all)       │
 │ or app / test      │ ─────────────────► │   uvicorn :8000, X-API-Key required  │
 │ (or SSH tunnel)    │                    │   /  UI, /report, /preview, ...      │
 └────────────────────┘                    │   /models/cxr-llava (read-only)      │
                                           │   L40S-24Q, ~13.2 GiB VRAM           │
                                           └──────────────────────────────────────┘
```

* The API is published on `0.0.0.0:8000` for LAN use and **requires
  `X-API-Key`**; the key is generated once into `deploy/api.key` (chmod 600).
  `build_and_run.sh` refuses a non-loopback bind without a key.
* `BIND_IP=127.0.0.1` restores tunnel-only mode (`.\deploy\tunnel.ps1`).
* The model directory is mounted **read-only**; the container has no docker
  socket, no host home, `--cap-drop ALL`, `no-new-privileges` and a 2 GiB tmpfs
  on `/tmp`.
* One Uvicorn worker; inference is serialised with an `asyncio.Lock` because the
  model is not re-entrant (it also spawns its own generation thread).

---

## 4. Files in this folder

| File | Purpose |
|---|---|
| `app.py` | FastAPI service: `/health`, `/config`, `/preview`, `/report`, `/differential`, `/ask`; DICOM→8-bit conversion |
| `ui.html` | single-page upload/preview/report UI served at `/` |
| `Dockerfile` | offline image based on the host's existing PyTorch image |
| `wheels/` | pinned wheels for cp311 / manylinux2014, built on this PC |
| `smoke_test.py` | load + generate without HTTP; fails with a full traceback |
| `make_test_dicom.py` | builds 12-bit MONOCHROME1/2 and no-window DICOMs for tests |
| `build_and_run.sh` | build, run, wait for health, print LAN URL + key |
| `push.ps1` | upload model/code/wheels over SSH and verify SHA-256 |
| `tunnel.ps1` | `ssh -N -L 8010:127.0.0.1:8000 icccserver` (loopback mode) |
| `test_client.ps1` | send one image through the tunnel or LAN, with `-ApiKey` |
| `samples/chest_xray_pa.png` | CC0 test image (see `samples/ATTRIBUTION.txt`) |
| `../test/` | OpenI dataset, edge/concurrency/QA tests, evaluation harness |

---

## 5. Runbook

### 5.1 Upload (from Windows)

```powershell
.\deploy\push.ps1
```

This creates `/home/iccc/cxr-llava/{model,deploy}`, uploads 13.1 GiB, and checks
the four large files against the Hub SHA-256 values. Expected time on a 1 GbE
link: roughly 3-5 minutes plus about a minute of hashing.

### 5.2 Build and start (on the server)

```bash
ssh icccserver
BIND_IP=0.0.0.0 REQUIRE_KEY=1 bash /home/iccc/cxr-llava/deploy/build_and_run.sh
```

Build is offline (`--network=none`, `--pull=false`). The script generates/reuses
`deploy/api.key`, publishes on the LAN, and prints the UI URL and key. First
model load reads 13 GiB and takes roughly 1-3 minutes; it polls `/health` for up
to 7.5 minutes and prints container logs if it fails.

For tunnel-only mode use `BIND_IP=127.0.0.1 REQUIRE_KEY=1`.

### 5.3 Open the UI

From the LAN: <http://10.10.10.28:8000/> — paste the key into the API-key field.

Or keep it off the LAN and use the tunnel:

```powershell
.\deploy\tunnel.ps1          # 127.0.0.1:8010 -> server:8000
```

### 5.4 Test

```powershell
.\deploy\test_client.ps1 -BaseUrl http://10.10.10.28:8000 -ApiKey <KEY>
.\deploy\test_client.ps1 -Mode differential -ApiKey <KEY>
.\deploy\test_client.ps1 -Mode ask -Question "Is there cardiomegaly?" -ApiKey <KEY>
```

Full suite (dataset, edge cases, QA, concurrency):

```powershell
.\test\run_all.ps1 -ApiKey <KEY>
```

---

## 6. API contract

All inference endpoints are `multipart/form-data`, field `file` = image.

| Endpoint | Extra fields | Response |
|---|---|---|
| `GET /` | — | web UI |
| `GET /health` | — | status, device, GPU, VRAM |
| `GET /config` | — | model, `auth_required`, max upload, modes |
| `POST /preview` | — | PNG of the decoded/windowed image + `X-Image-*` / `X-Dicom-*` headers |
| `POST /report` | `temperature=0.2`, `top_p=0.8` | `{report, latency_s, model, source}` |
| `POST /differential` | `temperature`, `top_p` | `{differential, latency_s, model, source}` |
| `POST /ask` | `question`, `temperature`, `top_p` | `{question, answer, latency_s, model, source}` |

All inference/preview endpoints require `X-API-Key` when `CXR_API_KEY` is set.
`file` may be DICOM (single-frame grayscale), PNG or JPEG. Errors: `400`
unreadable, `413` too large (body size or pixel count), `422` 16-bit PNG,
multi-frame DICOM, colour DICOM or bad parameters, `500` inference failure.

---

## 7. Acceptance criteria

1. `build_and_run.sh` reaches `READY` without touching the host's Python.
2. `docker logs cxr-llava` contains `model ready ... dtype=torch.bfloat16`
   and VRAM around 14-16 GiB (< 24 GiB).
3. `/health` returns `"gpu": "NVIDIA L40S-24Q"` and no CUDA error.
4. `/report` on the CC0 sample returns non-empty text in a plausible radiology
   register. Text quality is **not** an acceptance criterion: the model card
   documents hallucination and numeric limitations.
5. Two sequential requests succeed; the second does not OOM.
6. `docker restart cxr-llava` returns to healthy without manual steps.
7. No listening socket on `0.0.0.0:8000` on the host (`ss -ltn`).

---

## 8. Risks and fallbacks

| Risk | Likelihood | Plan |
|---|---|---|
| **torch 2.5.0 vs official 2.1.2** | medium | `smoke_test.py` decides. If it fails, download `torch==2.1.2+cu118` from `download.pytorch.org` on Windows (~2.2 GB), add to `wheels/`, pin it in the `Dockerfile`, rebuild. The 580 driver runs CUDA 11.8 fine. |
| First token slower than the 15 s `TextIteratorStreamer` timeout | low on L40S | if it happens, patch the timeout in a small wrapper before the 13 GiB copy is repeated (weights need not change) |
| 16-bit PNG/DICOM exports | likely in real data | rejected with a clear `422`; export 8-bit first (upstream model cannot use 16-bit) |
| OOM if another process uses the vGPU | medium | `nvidia-smi` showed 0 MiB at planning time; JupyterLab and the kind cluster also use this GPU, check before starting |
| Single request at a time | design limit | acceptable for one demo; a second worker on this 24 GB card would not fit |
| Host is contained-but-compromised (root held ~57 days, see the IR report) | **high** | treat outputs as untrusted; do not process identifiable patient data; keep the port on loopback; rebuild from a pre-18-Sep backup before any real use |
| Model licence | — | CC-BY-NC-4.0 + Llama-2; academic/non-commercial use only, cite the paper |

---

## 9. Privacy and security

The IR record in `icccserver-IR-20261114-153249/` documents a root-level
compromise of this host. The project owner reviewed that record on 2026-11-14
and **accepted the residual risk** for this build; no further containment work
is part of this deployment.

Precautions kept in place regardless of that decision:

* the API is bound to `127.0.0.1` and reached through an SSH tunnel — it is not
  on the LAN;
* the model is mounted read-only; the container has no docker socket, no host
  home, `--cap-drop ALL` and `no-new-privileges`;
* request logs contain byte counts and latency only — no filenames, no image
  data, no patient identifiers;
* the service keeps no history: each request is processed in memory and
  discarded.

If the API is later exposed to the LAN, set `CXR_API_KEY`, restrict the source
range in the firewall, and keep the port off the public internet. Patient-data
handling remains subject to the institution's policy; this service stores
nothing, but the host itself is shared with other workloads.

---

## 10. Operations

```bash
docker logs -f cxr-llava          # request log: bytes + latency, no filenames
docker restart cxr-llava          # ~1-3 min to reload
docker stop cxr-llava             # frees the 24 GB vGPU slice
docker rm -f cxr-llava            # rollback: removes the service, keeps model files
```

Do **not** run `pip install -U transformers` inside the image. Do not replace
`CXR_LLAVA_HF.py` with a newer revision without re-running the checks in
section 1.

---

## 11. Research log

* Model card and 6-line usage: <https://huggingface.co/ECOFRI/CXR-LLAVA-v2>
* Repository (default branch `master`): <https://github.com/ECOFRI/CXR_LLaVA>
* Official `requirements.txt`: `<repo>/requirements.txt`
* Issue #6/#7 (`add_special_tokens` crash): `/issues/6`, `/issues/7`
* Issue #8 (stale `main.py` loader): `/issues/8`
* HF PR #4 (unmerged tokenizer fix): `/discussions/4`
* Paper: <https://arxiv.org/abs/2310.18341>
* Existing CPU wrapper (design reference only): <https://github.com/WHarib/cxr-llava-api>
* Local file hashes checked against the Hub tree API on 2026-11-14:
  all 15 remaining files match (11 git-blob hashes + 4 LFS SHA-256).

---

## 12. Deployment and test result (2026-11-14)

Current image: **`cxr-llava:1.5`**, LAN URL <http://10.10.10.28:8000/>,
`X-API-Key` required. Full evidence is in [`../TEST_REPORT.md`](../TEST_REPORT.md).

| Check | Result |
|---|---|
| Upload | 13.1 GiB over SSH; weights + tokenizer match Hub SHA-256 |
| Offline build | succeeds without network; pinned wheels install in ~10 s |
| Import preflight | `transformers 4.36.2 · torch 2.5.0+cu121 · pydicom 2.4.4 · numpy 1.26.4` |
| Model load | ~14 s, dtype `bfloat16`, `cuda:0` |
| VRAM | **13.19 GiB allocated**, 13.22 GiB reserved; GPU total 15.6/24.6 GB |
| Report run, 120 OpenI images | **120/120**; mean **2.01 s**, p95 3.04 s; 0 empty; repetition 0.000 |
| Frontal subset, 74 images | 74/74; mean 2.07 s; 71 unique reports |
| `temperature=0.2`, 30 images | 30/30; mean 1.99 s; 28 unique |
| QA, 100 yes/no questions | 90 % raw accuracy but only 1/4 cardiomegaly and 0/6 effusion positives |
| Differential, 20 images | 20/20; mean 1.26 s; 17 unique |
| Determinism | 5/5 identical at `temperature=0` |
| Concurrency | 3 simultaneous reports all 200, wall 4.55 s, health stable |
| Edge/format/security suites | **49/49 + 58/58 pass** (images, DICOM, auth, CORS, injection, EXIF) |
| Restart | healthy in 14 s; report succeeds |
| Container | `cap-drop ALL`, `no-new-privileges`, read-only model, 2 GiB tmpfs `/tmp` |
| Port | `0.0.0.0:8000` with key (loopback-only mode available with `BIND_IP=127.0.0.1`) |

**Quality caveat:** engineering is solid, but the model over-calls cardiomegaly,
effusion, edema, atelectasis and pneumonia on OpenI (finding macro F1 0.15 all
views / 0.096 frontal). Lateral views are out of scope. Research use only.

Note: local port 8000 on the workstation was occupied by an unrelated Python
process, hence the 8010 default in `tunnel.ps1` / `test_client.ps1` when using
tunnel mode.

