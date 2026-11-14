"""Verify a downloaded MedGemma 1.5 4B folder before uploading it.

Checks:
  * all files from the HF repo are present (plus duplicate/browser artefacts)
  * duplicate `config (1).json` / index copies are byte-identical
  * safetensors shard sizes sum to the index's total_size
  * each safetensors header parses and its offsets fit the file
  * config architecture / dtype / image size are the expected Gemma 3 values

Usage:
  python medgemma/verify_model.py medgemma-1.5-4b-it
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys

EXPECTED = {
    ".gitattributes", "README.md", "added_tokens.json", "chat_template.jinja",
    "config.json", "generation_config.json", "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors", "model.safetensors.index.json",
    "preprocessor_config.json", "processor_config.json", "special_tokens_map.json",
    "tokenizer.json", "tokenizer.model", "tokenizer_config.json",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="medgemma-1.5-4b-it")
    args = parser.parse_args()
    root = pathlib.Path(args.path)
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 2

    problems: list[str] = []
    present = {p.name for p in root.iterdir() if p.is_file()}
    if "gitattributes" in present:
        print("note: 'gitattributes' is the downloaded .gitattributes (leading dot lost)")
        present.add(".gitattributes")
    missing = sorted(EXPECTED - present)
    if missing:
        problems.append(f"missing files: {missing}")
    extras = sorted(present - EXPECTED - {"gitattributes", "config (1).json",
                                          "model.safetensors.index (1).json"})
    if extras:
        print(f"note: extra files: {extras}")

    # Browser duplicates must be identical, otherwise the folder is ambiguous.
    for dup, original in (
        ("config (1).json", "config.json"),
        ("model.safetensors.index (1).json", "model.safetensors.index.json"),
    ):
        if (root / dup).is_file():
            same = sha256(root / dup) == sha256(root / original)
            print(f"{'OK  ' if same else 'FAIL'} duplicate {dup} == {original}")
            if not same:
                problems.append(f"{dup} differs from {original}")

    index_path = root / "model.safetensors.index.json"
    if not index_path.is_file():
        print("FAIL: no index")
        return 1
    index = json.loads(index_path.read_text())
    shards = sorted(set(index["weight_map"].values()))
    total = int(index["metadata"]["total_size"])
    file_bytes = sum((root / shard).stat().st_size for shard in shards)
    print(f"shards: {shards}")
    print(f"index tensor bytes: {total:,}; shard files: {file_bytes:,}; "
          f"header/alignment overhead: {file_bytes - total:+,}")

    data_bytes = 0
    for shard in shards:
        path = root / shard
        with path.open("rb") as handle:
            header_len = struct.unpack("<Q", handle.read(8))[0]
            header = json.loads(handle.read(header_len))
        tensors = {k: v for k, v in header.items() if k != "__metadata__"}
        max_end = max(v["data_offsets"][1] for v in tensors.values())
        data_bytes += max_end
        file_size = path.stat().st_size
        fits = 8 + header_len + max_end <= file_size
        print(f"{'OK  ' if fits else 'FAIL'} {shard}: {len(tensors)} tensors, "
              f"header {header_len / 1e6:.1f} MB, data {max_end / 1e9:.3f} GB, "
              f"file {file_size / 1e9:.3f} GB")
        if not fits:
            problems.append(f"{shard} tensor offsets exceed file size")
        if header_len > 200_000_000:
            problems.append(f"{shard} header length implausible")

    print(f"tensor data from headers: {data_bytes:,}; index: {total:,}; "
          f"diff: {data_bytes - total:+,}")
    if data_bytes != total:
        problems.append("tensor data does not equal index total_size")

    cfg = json.loads((root / "config.json").read_text())
    print("architectures:", cfg.get("architectures"))
    print("dtype:", cfg.get("torch_dtype"), "| image_size:",
          cfg.get("vision_config", {}).get("image_size"),
          "| text layers:", cfg.get("text_config", {}).get("num_hidden_layers"))
    if cfg.get("architectures") != ["Gemma3ForConditionalGeneration"]:
        problems.append("unexpected architecture")
    if cfg.get("torch_dtype") != "bfloat16":
        problems.append("unexpected dtype")
    if cfg.get("vision_config", {}).get("image_size") != 896:
        problems.append("unexpected image size")

    proc = json.loads((root / "processor_config.json").read_text())
    print("processor keys:", sorted(proc)[:12])
    print("chat template:", "present" if (root / "chat_template.jinja").is_file() else "missing")
    if not (root / "chat_template.jinja").is_file():
        problems.append("chat_template.jinja missing")

    print()
    if problems:
        print("FAIL")
        for problem in problems:
            print(" -", problem)
        return 1
    size_gib = sum(p.stat().st_size for p in root.iterdir() if p.is_file()) / 2**30
    print(f"PASS: model folder is complete and internally consistent ({size_gib:.2f} GiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
