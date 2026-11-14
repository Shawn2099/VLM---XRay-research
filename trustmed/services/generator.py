"""Client for the report-generation service (CXR-LLaVA or MedGemma)."""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from .. import config


class BackendError(RuntimeError):
    pass


def _headers() -> dict:
    key = config.backend_key()
    return {"X-API-Key": key} if key else {}


def info() -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            body = client.get(f"{config.BACKEND_URL}/config", headers=_headers()).json()
        return {"ok": True, **body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def generate(stored_path: str, content_type: str, prompt: str = "") -> tuple[str, int]:
    """POST the image to /report and return (text, latency_ms)."""
    path = Path(stored_path)
    if not path.is_file():
        raise BackendError("stored image is missing")

    if content_type in {"application/dicom", "application/dicom+json"} or path.suffix.lower() in {
        ".dcm",
        ".dicom",
    }:
        mime = "application/dicom"
    elif path.suffix.lower() in {".png"}:
        mime = "image/png"
    else:
        mime = "image/jpeg"

    data = {"temperature": "0", "top_p": "1"}
    if prompt:
        data["prompt"] = prompt

    started = time.perf_counter()
    try:
        with path.open("rb") as handle, httpx.Client(timeout=300) as client:
            response = client.post(
                f"{config.BACKEND_URL}/report",
                headers=_headers(),
                files={"file": (path.name, handle, mime)},
                data=data,
            )
    except httpx.HTTPError as exc:
        raise BackendError(f"report service unreachable: {exc}") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)

    if response.status_code == 401:
        raise BackendError("report service rejected the API key")
    if response.status_code != 200:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            detail = response.text[:200]
        raise BackendError(f"report service returned {response.status_code}: {detail}")

    text = (response.json().get("report") or "").strip()
    if not text:
        raise BackendError("report service returned an empty report")
    return text, latency_ms
