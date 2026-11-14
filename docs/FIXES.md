# TrustMed — what we fixed

**Status:** the phase-I report is no longer the specification. This file is.
Everything below is either measured on our own runs or decided for a reason that is written next to it.

Last updated: 2026-11-15

---

## 1. Claims in the report that were wrong, and what replaces them

| # | Report claimed | Reality | Now |
|---|---|---|---|
| 1 | DenseNet-121 verifies reports | no code existed | DenseNet-121 is the **candidate** verifier, gated on a measured AUC test before it is trusted |
| 2 | Consistency score `Sc = n_sup/n_find` | never implemented | replaced by a **five-state verdict per finding** (supported · uncertain · unsupported · contradiction · omission) |
| 3 | Semantic entropy `H̃` (Eq. 6.1–6.2) | never implemented; needs NLI + N× generation | **dropped**; no replacement in v1 |
| 4 | Anomaly score `A` | never defined, no data to fit it | **dropped** |
| 5 | Confidence `C = w₁Sc + w₂(1−H̃) + w₃(1−A)` | three unvalidated terms, hand-picked weights | **calibrated function of verdicts only**, fitted on held-out studies |
| 6 | `Verified` / `Review Required` | "Verified" reads as clinical validation | `Auto-accepted` / `Review suggested` / `Review required` |
| 7 | Flask + MySQL + login + roles + review | none existed | **FastAPI + SQLite**, 2 roles + admin flag, review + audit |
| 8 | MIMIC-CXR is the principal corpus | no DUA, no data | **OpenI-500** is the corpus; MIMIC is future work |
| 9 | 2 Kaggle pneumonia/COVID/TB sets | no reports → cannot evaluate generation | **dropped** |
| 10 | "Real patient data is used for testing" | untrue, and contradicts §4.2 | **removed** |
| 11 | CLAHE improves reports | never ablated; model never saw CLAHE | **not used by default**; model's own preprocessing |
| 12 | ~30 s end-to-end | never measured | replaced by measured latency |
| 13 | Abstract: "is evaluated … BLEU, ROUGE, CheXbert" | no results at the time | 500-study results now exist and are cited |
| 14 | §6.3 numbered twice, §6.3.3 ends mid-sentence | typographic faults | fixed in the rewrite |

## 2. Locked defaults — do not change without a measurement

| Default | Value | Evidence |
|---|---|---|
| Generator | CXR-LLaVA v1.5 (`cxr-llava:1.5`) | 500/500, **1.96 s**, macro F1 0.118 |
| Second backend | MedGemma 1.5 4B, installed but idle | 3.61 s, macro 0.186 — fallback + paper baseline |
| Finding extractor | CheXbert (`f1chexbert` 0.0.2) | 14 labels verified, 0.12 s/report |
| Image verifier | **DenseNet-121, pending AUC gate** | see §5 |
| Corpus | OpenI-500 frontal | 2 172 candidates → 500, deduplicated |
| Database | SQLite | one file, no server |
| Web | FastAPI + Jinja + htmx | already deployed |
| UI design | `trustmed_prototype .zip` | palette, rail, score bar, highlighting |

## 3. Dropped from scope (with the reason, so it looks chosen)

| Dropped | Reason | Where it lives now |
|---|---|---|
| Semantic entropy / N-sample clustering | needs NLI model + 4× generation cost; redundant with a second model's opinion | future work |
| Anomaly detection | undefined input space, no training data | deleted |
| MIMIC-CXR | blocked on CITI + DUA | future work |
| Kaggle pneumonia/COVID/TB | no free-text reports | deleted |
| MySQL / Flask | SQLite + FastAPI already working | deleted |
| "Verified" status | unsafe clinical wording | renamed |
| 3rd role (Admin as separate actor) | user management is a flag, not an actor | folded in |
| PDF export | browser print-to-PDF is enough | deleted |
| Grad-CAM | not needed for any claim; last-day extra | optional |
| Self-consistency sampling | 4× latency, adds little over the classifier | future work |

## 4. Guardrails that must exist in code

| # | Guardrail | Blocks |
|---|---|---|
| G1 | Assert the 18→14 label mapping and polarity on 3 fixture reports at startup | silent wrong verdicts |
| G2 | DenseNet per-finding AUC on OpenI-500 before the UI trusts it | building on a bad classifier |
| G3 | Per-finding thresholds from that run — never a global 0.5 | arbitrary flags |
| G4 | Omission only when `p ≥ 0.90` **and** that finding's PPV ≥ 0.5 | flag spam |
| G5 | Four label states (`+1 / −1 / blank`) preserved to the verdict engine | blank read as "absent" |
| G6 | Patient-level split + leakage check before fitting calibration | inflated ECE/AUC |
| G7 | Every report stores model version, prompt hash, thresholds used | irreproducible results |
| G8 | No `Auto-accepted` for a report with fewer than 3 findings | catch-all "normal" gaming the score |

## 5. The verifier gate — measured, decided

Run on 500 OpenI studies against CheXbert labels from the reference report, with
three pretrained DenseNet-121 weight sets (`all`, `chex`, `mimic_ch`).

**Result: only pleural effusion clears AUC 0.80** (0.822 / 0.776 / 0.826).
Cardiomegaly peaks at 0.744; atelectasis 0.710; everything else 0.53–0.67.

Decision, now enforced in code (`verdict.MIN_AUC = 0.75`):

* pleural effusion is verified;
* all other findings are reported as **not assessable** — grey in the UI, never
  counted as correct, never used for omissions.

Why the numbers are a lower bound (stated in the report):

* the 500-study set still contains **lateral views** (the frontal filter accepted
  square images);
* reference labels come from terse OpenI reports (effusion prevalence 3.6 %), so
  a correct image model is scored as a false positive.

Full table: `docs/VERIFIER_GATE.md`, `docs/VALIDATION.md`.

## 6. Known risks we accept, and disclose

- CheXbert and DenseNet both derive from the CheXpert ontology → **correlated errors**. Agreement is a second opinion, never ground truth.
- OpenI is small and terse; results are zero-shot and do not transfer to a hospital.
- CheXbert licence is Stanford academic / non-commercial.
- Neither model is clinically usable: omission is 68–71 % on the 500-study set.
- The UI is a research prototype; no PHI, no PACS, no CE/MDR claim.

## 7. Report edits required (mechanical)

- Abstract: OpenI-500, present tense, add RadGraph/BERTScore/CIs.
- §4.2: DICOM is **in** scope (it is implemented).
- §5.6 Table 5.1: FastAPI, SQLite, CheXbert, DenseNet-121; remove semantic-entropy row.
- §6.1–6.4: as §1 above; delete Eq. 6.1, 6.2, 6.4; renumber; finish the truncated sentence.
- §8: semantic entropy, MIMIC, fine-tuning, PACS.
- §9: "implemented", not "prototyped".
- Typos: `feautres`, `Estimationt`, `R PTANISHQA`, `Trustmed`.
