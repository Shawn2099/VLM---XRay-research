# Test suite — CXR-LLaVA service

Everything here runs against the **deployed** HTTP service, so it exercises the
same path the application uses (FastAPI, DICOM/PNG decoding, API key, model).

## 1. Dataset

`test/data/openi/` holds **120 OpenI / Indiana University chest X-rays** with
the FINDINGS section of their reports.

* original source: NLM Open-i <https://openi.nlm.nih.gov/faq> (site was under
  maintenance on 2026-11-14)
* mirror used: <https://huggingface.co/datasets/Shrey-1329/cxiu_hf_dataset>
* 512×624 JPEG, 22 MB total, 120 unique reports
* re-fetch: `python test/fetch_openi.py` (caches the 369 MB parquet shard)

`test/data/dicom/` holds 3 synthetic 12-bit DICOMs (from the CC0 sample) and
pydicom-data files covering JPEG 2000, JPEG lossless, JPEG-LS, RLE,
multi-frame, colour and uncompressed transfer syntaxes. `test/data/dicom/extra/`
adds signed pixels, zero window, no preamble, missing PixelData/Rows and a
CRLF-injection tag.

The OpenI subset is public but **research use only**; it is not patient data
from Saintgits.

## 2. Scripts

| script | what it proves |
|---|---|
| `edge_cases.py` | formats (PNG/JPEG/RGBA/palette), 16-bit rejection, corrupt/empty/oversized input, auth, `/docs` disabled, DICOM transfer syntaxes, multi-frame/colour rejection |
| `fetch_openi_large.py` | builds the 500-study frontal OpenI set (`test/data/openi500`) |
| `evaluate_api.py` | 120/500-image report run: success/error/empty rates, latency, repetition, unigram F1 and negation-aware finding precision/recall/F1 vs the OpenI reports |
| `qa_test.py` | cardiomegaly / effusion yes-no questions; polarity accuracy vs the reference |
| `qa_balanced.py` | balanced positive/negative QA set with sensitivity, specificity, PPV, NPV and Wilson CIs |
| `qa_rescore.py` | re-scores stored QA JSON with the current polarity parser (no GPU) |
| `bootstrap_ci.py` | 1,000-resample 95 % CIs for macro/finding F1 and unigram F1 |
| `paired_bootstrap.py` | paired bootstrap difference and p-value between two backends |
| `report_metrics.py` | CheXbert/RadGraph/BLEU/ROUGE/BERTScore (run in `metrics-venv`) |
| `preprocess_ablation.py` | original 8-bit image vs synthetic 16-bit DICOM, paired |
| `disagreement.py` | agreement, who-is-right and deferral/risk–coverage analysis between two backends |
| `compare_backends.py` | builds the CXR-LLaVA vs MedGemma markdown table from summaries |
| `endpoint_matrix.py` | `/differential` on 20 images, determinism at temperature 0, definitional questions |
| `concurrency_test.py` | 3 simultaneous reports queue behind the model lock and all succeed; `/health` stays OK |
| `make_extra_dicom.py` | builds signed, zero-window, no-preamble, missing-tag, 8-bit and LUT DICOMs |
| `run_all.ps1` | runs all of the above and tees everything to `test/results/run.log` |

All suites work against **either backend** — point `--base-url` at the active
one (`http://10.10.10.28:8000`). Switch with
`.\medgemma\switch.ps1 -Model cxr|medgemma`.

The finding detector is deliberately simple keyword matching with a negation
scope. It is a **screening metric**, not a clinical NLP evaluation; read the
stored examples rather than trusting the F1 alone.

## 3. Run

The service must be reachable (LAN or SSH tunnel). From the workstation:

```powershell
# one suite
python test\edge_cases.py --api-key <KEY>
python test\evaluate_api.py --api-key <KEY> --temperature 0 --limit 120
python test\qa_test.py --api-key <KEY> --limit 25
python test\concurrency_test.py --api-key <KEY> --workers 3

# everything
.\test\run_all.ps1 -ApiKey <KEY>
```

Outputs:

```
test/results/report_t0/summary.json     machine-readable metrics
test/results/report_t0/summary.md       human-readable table + examples
test/results/report_t0/results.jsonl    every report and reference
test/results/report_t02/                temperature 0.2 subset
test/results/qa.json                    yes/no answers
test/results/run.log                    full console log
```

## 4. Interpreting the numbers

* **Latency**: wall-clock from the client, including upload and model time.
  The service handles one request at a time; concurrent clients queue.
* **Finding F1**: agreement between "the report mentions X" and "the reference
  mentions X", with a crude negation window. Reports often describe findings
  differently, so low F1 is not automatically a bug.
* **Unigram F1**: content-word overlap with the reference findings. Useful for
  regression tracking, not for clinical accuracy.
* **Repetition**: fraction of repeated 8-grams; >0.1 usually means a degenerate
  generation.
* **QA accuracy**: the model may answer "no" to a finding the reference reports
  (or vice versa); `qa.json` keeps every answer for review.

## 5. Notes

* The model's upstream licence is CC-BY-NC-4.0 plus Llama-2; these tests are
  non-commercial research use.
* Do not run the suite against a service that is handling real patient data.
  The test images are written to `test/data/` on the workstation.
* The service stores nothing; results are written only by these scripts.
