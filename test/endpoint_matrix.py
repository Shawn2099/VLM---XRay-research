"""Endpoint matrix: /differential, determinism, and definitional /ask.

Run: python test/endpoint_matrix.py --api-key KEY
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "openi"


def post(base, key, path, endpoint, data, timeout=300):
    started = time.time()
    with path.open("rb") as handle:
        response = requests.post(
            f"{base}/{endpoint}",
            headers={"X-API-Key": key},
            files={"file": (path.name, handle, "image/jpeg")},
            data=data,
            timeout=timeout,
        )
    return response, time.time() - started


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", default="test/results/endpoints.json")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key")

    metadata = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.limit]

    differential = []
    for record in metadata:
        response, elapsed = post(
            args.base_url, args.api_key, DATA / record["file"], "differential",
            {"temperature": "0", "top_p": "1"},
        )
        body = response.json()
        differential.append(
            {
                "id": record["id"],
                "status": response.status_code,
                "latency_s": round(elapsed, 2),
                "text": (body.get("differential") or "").strip(),
            }
        )
    print(f"differential: {len(differential)} requests", flush=True)

    determinism = []
    for record in metadata[:5]:
        texts = []
        for _ in range(2):
            response, elapsed = post(
                args.base_url, args.api_key, DATA / record["file"], "report",
                {"temperature": "0", "top_p": "1"},
            )
            texts.append((response.json().get("report") or "").strip())
        determinism.append(
            {"id": record["id"], "identical": texts[0] == texts[1], "text": texts[0]}
        )
    print("determinism: 5 images x 2", flush=True)

    definitional = []
    for record in metadata[:5]:
        response, elapsed = post(
            args.base_url, args.api_key, DATA / record["file"], "ask",
            {"question": "What is the meaning of consolidation?",
             "temperature": "0", "top_p": "1"},
        )
        body = response.json()
        definitional.append(
            {
                "id": record["id"],
                "status": response.status_code,
                "latency_s": round(elapsed, 2),
                "answer": (body.get("answer") or "").strip(),
            }
        )

    summary = {
        "differential": {
            "n": len(differential),
            "ok": sum(1 for r in differential if r["status"] == 200 and r["text"]),
            "empty": sum(1 for r in differential if r["status"] == 200 and not r["text"]),
            "latency_mean_s": round(statistics.mean(r["latency_s"] for r in differential), 2),
            "unique": len({r["text"] for r in differential}),
        },
        "determinism": {
            "n": len(determinism),
            "identical": sum(1 for r in determinism if r["identical"]),
        },
        "definitional": {
            "n": len(definitional),
            "ok": sum(1 for r in definitional if r["status"] == 200 and r["answer"]),
            "sample": definitional[0]["answer"][:400] if definitional else "",
        },
        "details": {
            "differential": differential,
            "determinism": determinism,
            "definitional": definitional,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "details"}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
