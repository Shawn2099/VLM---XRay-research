"""Fetch a diverse subset of the OpenI chest X-ray dataset from Hugging Face.

The NLM Open-i archive is unavailable ("under maintenance"), so this uses the
public mirror `Shrey-1329/cxiu_hf_dataset` (6,060 OpenI image + FINDINGS pairs).
Downloading one parquet shard and extracting ~120 unique reports is far more
reliable than 120 signed image URLs, and the shard is cached for re-runs.

Writes:
    test/data/openi/0000.jpg ...
    test/data/openi/metadata.jsonl
    test/data/openi/ATTRIBUTION.txt

Run:  python test/fetch_openi.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import pyarrow.parquet as pq
import requests

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "openi"
PARQUET = ROOT / "data" / "train-00000-of-00003.parquet"
SHARD_URL = (
    "https://huggingface.co/datasets/Shrey-1329/cxiu_hf_dataset/resolve/main/"
    "data/train-00000-of-00003-34bea7eff0b2e45b.parquet"
)
TARGET = 120

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def download(url: str, destination: pathlib.Path) -> None:
    if destination.exists() and destination.stat().st_size > 100_000_000:
        print(f"cached: {destination} ({destination.stat().st_size / 1e6:.0f} MB)")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_suffix(".part")
    with requests.get(url, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        written = 0
        started = time.time()
        last = 0.0
        with part.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)
                if time.time() - last > 5:
                    last = time.time()
                    rate = written / max(0.1, time.time() - started) / 1e6
                    if total:
                        print(f"  {written / 1e6:.0f}/{total / 1e6:.0f} MB  {rate:.1f} MB/s",
                              flush=True)
    part.rename(destination)
    print(f"downloaded {destination} ({destination.stat().st_size / 1e6:.0f} MB)")


def image_bytes(value) -> bytes | None:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, dict):
        data = value.get("bytes")
        if data is not None:
            return bytes(data)
        path = value.get("path")
        if path and pathlib.Path(path).is_file():
            return pathlib.Path(path).read_bytes()
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=TARGET)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    download(SHARD_URL, PARQUET)

    print("reading parquet...", flush=True)
    table = pq.read_table(PARQUET, columns=["image", "text"])
    texts = table.column("text").to_pylist()
    images = table.column("image").to_pylist()
    total = table.num_rows
    print(f"{total} rows in shard")

    # Spread the picks across the shard so one report/patient does not dominate.
    stride = max(1, total // (args.target * 4))
    candidates = list(range(0, total, stride)) + list(range(total))

    seen: set[str] = set()
    records: list[dict] = []
    for row_idx in candidates:
        text = " ".join((texts[row_idx] or "").split())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        data = image_bytes(images[row_idx])
        if not data:
            continue
        seen.add(key)

        index = len(records)
        extension = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        name = f"{index:04d}{extension}"
        (OUT / name).write_bytes(data)
        records.append(
            {
                "id": f"{index:04d}",
                "row_idx": row_idx,
                "file": name,
                "bytes": len(data),
                "findings": text,
            }
        )
        if len(records) >= args.target:
            break

    with (OUT / "metadata.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    (OUT / "ATTRIBUTION.txt").write_text(
        "OpenI / Indiana University Chest X-ray collection\n"
        "Source: https://openi.nlm.nih.gov/faq (NLM Open-i)\n"
        "Mirror: https://huggingface.co/datasets/Shrey-1329/cxiu_hf_dataset\n"
        "Reports are the FINDINGS sections. Research use only.\n"
        f"Downloaded subset: {len(records)} unique reports on 2026-11-14.\n",
        encoding="utf-8",
    )
    size = sum((OUT / r["file"]).stat().st_size for r in records)
    print(f"wrote {len(records)} images, {size / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
