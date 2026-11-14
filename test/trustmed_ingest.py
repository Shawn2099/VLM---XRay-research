"""Ingest contract: what TrustMed must accept and must refuse.

    python test/trustmed_ingest.py --base http://127.0.0.1:8010
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys
import tempfile

import numpy as np
import requests
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def upload(session, base, name, raw, mime):
    response = session.post(
        f"{base}/api/upload", files={"file": (name, io.BytesIO(raw), mime)}, timeout=120
    )
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8010")
    args = parser.parse_args()

    session = requests.Session()
    session.post(
        f"{args.base}/auth/login",
        data={"email": "admin@trustmed.local", "password": "trustmed-admin"},
        allow_redirects=False,
        timeout=30,
    )

    # 1. real DICOM (MONOCHROME1, 16-bit)
    dicom = DATA / "dicom" / "test_cxr_mono1.dcm"
    if dicom.is_file():
        response = upload(session, args.base, dicom.name, dicom.read_bytes(), "application/dicom")
        body = response.json() if response.ok else {}
        check(
            "DICOM accepted",
            response.status_code == 200 and body.get("source") == "dicom",
            f"{response.status_code} {body.get('source')}",
        )
    else:
        check("DICOM accepted", False, "fixture missing")

    # 2. 16-bit PNG must be refused with a useful message
    buffer = io.BytesIO()
    Image.fromarray((np.arange(256 * 256) % 4096).astype(np.uint16).reshape(256, 256)).save(
        buffer, format="PNG"
    )
    response = upload(session, args.base, "sixteen.png", buffer.getvalue(), "image/png")
    check("16-bit PNG refused", response.status_code == 422,
          f"{response.status_code} {response.json().get('detail', '')[:50]}")

    # 3. colour photo must be refused
    rgb = np.zeros((256, 256, 3), dtype=np.uint8)
    rgb[..., 0] = 200
    rgb[..., 1] = 40
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="PNG")
    response = upload(session, args.base, "photo.png", buffer.getvalue(), "image/png")
    check("colour photo refused", response.status_code == 422,
          f"{response.status_code} {response.json().get('detail', '')[:40]}")

    # 4. non-image bytes must be refused
    response = upload(session, args.base, "notes.txt", b"not an image at all", "text/plain")
    check("garbage refused", response.status_code in {415, 422}, f"{response.status_code}")

    # 5. a good PNG is accepted and deduplicated by hash
    good = DATA / "openi500" / "0001.png"
    first = upload(session, args.base, "a.png", good.read_bytes(), "image/png")
    second = upload(session, args.base, "b.png", good.read_bytes(), "image/png")
    check(
        "PNG accepted",
        first.status_code == 200 and first.json().get("source") == "image",
        f"{first.status_code}",
    )
    check(
        "same bytes -> same image id",
        first.ok and second.ok and first.json()["image_id"] == second.json()["image_id"],
    )

    print("=== ingest contract ===")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<26} {detail}")
    failures = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
