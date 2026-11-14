"""Build a larger OpenI test set (default 500 unique frontal reports).

Reads all three parquet shards of the HF mirror, deduplicates by report text,
keeps portrait/square images (likely frontal), and samples evenly across the
shards so the set is not clustered in one part of the collection.

Writes:
    test/data/openi500/0000.jpg ...
    test/data/openi500/metadata.jsonl
    test/data/openi500/ATTRIBUTION.txt

Run: python test/fetch_openi_large.py --target 500
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib

import pyarrow.parquet as pq
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "openi500"
SHARDS = [
    DATA / "train-00000-of-00003.parquet",
    DATA / "train-00001-of-00003.parquet",
    DATA / "train-00002-of-00003.parquet",
]


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
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--all-views", action="store_true")
    args = parser.parse_args()

    missing = [str(path) for path in SHARDS if not path.is_file()]
    if missing:
        raise SystemExit(f"missing shards: {missing}")

    OUT.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    candidates: list[dict] = []

    for shard_index, path in enumerate(SHARDS):
        print(f"reading {path.name}...", flush=True)
        table = pq.read_table(path, columns=["image", "text"])
        texts = table.column("text").to_pylist()
        images = table.column("image").to_pylist()
        for row_idx, (text, image) in enumerate(zip(texts, images)):
            text = " ".join((text or "").split())
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            data = image_bytes(image)
            if not data:
                continue
            try:
                with Image.open(io.BytesIO(data)) as decoded:
                    width, height = decoded.size
            except Exception:
                continue
            if not args.all_views and height < width:
                continue
            seen.add(key)
            candidates.append(
                {
                    "shard": shard_index,
                    "row_idx": row_idx,
                    "bytes": data,
                    "width": width,
                    "height": height,
                    "findings": text,
                }
            )
        print(f"  {len(candidates)} unique candidates so far", flush=True)

    candidates.sort(key=lambda item: (item["shard"], item["row_idx"]))
    if len(candidates) > args.target:
        step = len(candidates) / args.target
        selected = [candidates[int(i * step)] for i in range(args.target)]
    else:
        selected = candidates
    print(f"selected {len(selected)} of {len(candidates)} candidates")

    records = []
    for index, item in enumerate(selected):
        data = item.pop("bytes")
        extension = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        name = f"{index:04d}{extension}"
        (OUT / name).write_bytes(data)
        records.append(
            {
                "id": f"{index:04d}",
                "shard": item["shard"],
                "row_idx": item["row_idx"],
                "file": name,
                "width": item["width"],
                "height": item["height"],
                "findings": item["findings"],
                "bytes": len(data),
            }
        )

    with (OUT / "metadata.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    (OUT / "ATTRIBUTION.txt").write_text(
        "OpenI / Indiana University Chest X-ray collection\n"
        "Source: https://openi.nlm.nih.gov/faq (NLM Open-i)\n"
        "Mirror: https://huggingface.co/datasets/Shrey-1329/cxiu_hf_dataset\n"
        "Reports are the FINDINGS sections. Research use only.\n"
        f"Large subset: {len(records)} unique reports, frontal/square only.\n",
        encoding="utf-8",
    )
    size = sum((OUT / record["file"]).stat().st_size for record in records)
    print(f"wrote {len(records)} images, {size / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
