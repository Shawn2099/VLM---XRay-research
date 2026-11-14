"""RQ2 ablation: original 8-bit image vs 16-bit DICOM through the service.

For N OpenI images, sends (a) the original JPEG/PNG and (b) a synthetic 12-bit
DICOM generated from the same pixels. Compares report quality against the
reference and reports the paired difference.

Run against each backend:
  python test/preprocess_ablation.py --api-key KEY --limit 50 \
      --out test/results/preprocess_medgemma.json
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import statistics
import sys
import tempfile
import time

import numpy as np
import pydicom
import requests
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from evaluate_api import LABELS, mentions, unigram_f1  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "openi500"


def make_dicom(image: Image.Image, path: pathlib.Path) -> None:
    pixels = np.asarray(image.convert("L"), dtype=np.uint16)
    pixels = (pixels.astype(np.uint32) * 4095 // 255).astype(np.uint16)
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.PatientName = "TEST^PUBLIC"
    ds.PatientID = "CC0-TEST"
    ds.Modality = "CR"
    ds.BodyPartExamined = "CHEST"
    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.WindowCenter = 2048
    ds.WindowWidth = 4096
    ds.PixelData = pixels.astype("<u2").tobytes()
    ds.save_as(str(path), write_like_original=False)


def post(base, key, path, content_type):
    started = time.time()
    with path.open("rb") as handle:
        response = requests.post(
            f"{base}/report",
            headers={"X-API-Key": key},
            files={"file": (path.name, handle, content_type)},
            data={"temperature": "0", "top_p": "1"},
            timeout=300,
        )
    return response, time.time() - started


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", default="test/results/preprocess.json")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key")

    metadata = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.limit]

    rows = []
    with tempfile.TemporaryDirectory() as temp:
        tempdir = pathlib.Path(temp)
        for index, record in enumerate(metadata, 1):
            source = DATA / record["file"]
            with Image.open(source) as image:
                dicom_path = tempdir / f"{record['id']}.dcm"
                make_dicom(image, dicom_path)
            raw_response, raw_latency = post(args.base_url, args.api_key, source,
                                             "image/jpeg")
            dicom_response, dicom_latency = post(args.base_url, args.api_key,
                                                 dicom_path, "application/dicom")
            raw_text = (raw_response.json().get("report") or "").strip()
            dicom_text = (dicom_response.json().get("report") or "").strip()
            rows.append(
                {
                    "id": record["id"],
                    "reference": record["findings"],
                    "raw": raw_text,
                    "dicom": dicom_text,
                    "raw_latency_s": round(raw_latency, 2),
                    "dicom_latency_s": round(dicom_latency, 2),
                    "raw_status": raw_response.status_code,
                    "dicom_status": dicom_response.status_code,
                }
            )
            if index % 10 == 0:
                print(f"{index}/{len(metadata)}", flush=True)

    ok = [row for row in rows if row["raw_status"] == 200 and row["dicom_status"] == 200]
    summary = {"n": len(ok), "conditions": {}}
    for condition in ("raw", "dicom"):
        texts = [row[condition] for row in ok]
        uf1 = [unigram_f1(text, row["reference"]) for text, row in zip(texts, ok)]
        label_f1 = {}
        for label, pattern in LABELS.items():
            tp = fp = fn = 0
            for text, row in zip(texts, ok):
                ref = mentions(row["reference"], pattern)
                pred = mentions(text, pattern)
                if ref and pred:
                    tp += 1
                elif pred:
                    fp += 1
                elif ref:
                    fn += 1
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            label_f1[label] = round(
                2 * precision * recall / (precision + recall)
                if precision + recall else 0.0, 3
            )
        summary["conditions"][condition] = {
            "unigram_f1": round(statistics.mean(uf1), 4) if uf1 else 0,
            "macro_f1": round(statistics.mean(label_f1.values()), 4),
            "labels": label_f1,
            "latency_mean_s": round(
                statistics.mean(row[f"{condition}_latency_s"] for row in ok), 2
            ),
        }
    summary["delta_dicom_minus_raw_unigram"] = round(
        summary["conditions"]["dicom"]["unigram_f1"]
        - summary["conditions"]["raw"]["unigram_f1"], 4
    )
    summary["rows"] = rows
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
