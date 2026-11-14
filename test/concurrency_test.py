"""Concurrency check: two/three simultaneous report requests must queue, not crash.

Run: python test/concurrency_test.py --api-key KEY --workers 3
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent / "data" / "openi"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key")

    metadata = [
        json.loads(line)
        for line in (DATA / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][: args.workers]
    if len(metadata) < args.workers:
        raise SystemExit("not enough images")

    def run(record):
        started = time.time()
        with (DATA / record["file"]).open("rb") as handle:
            response = requests.post(
                f"{args.base_url}/report",
                headers={"X-API-Key": args.api_key},
                files={"file": (record["file"], handle, "image/jpeg")},
                data={"temperature": "0", "top_p": "1"},
                timeout=600,
            )
        elapsed = time.time() - started
        body = response.json()
        return {
            "id": record["id"],
            "status": response.status_code,
            "wall_s": round(elapsed, 2),
            "model_latency_s": body.get("latency_s"),
            "chars": len(body.get("report", "")),
        }

    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run, metadata))
    total = time.time() - started

    health = requests.get(f"{args.base_url}/health", timeout=10).json()
    print(json.dumps({"results": results, "wall_s": round(total, 2), "health": health}, indent=2))
    ok = all(item["status"] == 200 and item["chars"] > 0 for item in results)
    raise SystemExit(0 if ok and health.get("status") == "ok" else 1)


if __name__ == "__main__":
    main()
