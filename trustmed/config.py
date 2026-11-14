"""TrustMed configuration.

Everything is environment-driven so the same code runs on the laptop and in the
container. Nothing secret is hard-coded.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("TRUSTMED_DATA", ROOT / "data_trustmed"))
DB_PATH = Path(os.environ.get("TRUSTMED_DB", DATA_DIR / "trustmed.db"))
IMAGE_DIR = Path(os.environ.get("TRUSTMED_IMAGES", DATA_DIR / "images"))
CALIBRATION_PATH = Path(os.environ.get("TRUSTMED_CALIBRATION", DATA_DIR / "calibration.json"))

# ------------------------------------------------------------------ generator
BACKEND_URL = os.environ.get("TRUSTMED_BACKEND", "http://10.10.10.28:8000").rstrip("/")
BACKEND_NAME = os.environ.get("TRUSTMED_BACKEND_NAME", "cxr-llava")


def backend_key() -> str:
    """API key for the report service: env first, then deploy/api.key."""
    key = os.environ.get("TRUSTMED_API_KEY", "").strip()
    if key:
        return key
    for candidate in (ROOT / "deploy" / "api.key", Path("/home/iccc/cxr-llava/deploy/api.key")):
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return ""


# ------------------------------------------------------------------ web / security
SECRET_KEY = os.environ.get("TRUSTMED_SECRET", "dev-only-change-me")
SESSION_HOURS = int(os.environ.get("TRUSTMED_SESSION_HOURS", "12"))
COOKIE_NAME = "trustmed_session"

ADMIN_EMAIL = os.environ.get("TRUSTMED_ADMIN_EMAIL", "admin@trustmed.local")
ADMIN_PASSWORD = os.environ.get("TRUSTMED_ADMIN_PASSWORD", "trustmed-admin")

MAX_UPLOAD_BYTES = int(os.environ.get("TRUSTMED_MAX_UPLOAD", str(40 * 1024 * 1024)))
MAX_PIXELS = 40_000_000
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".dcm", ".dicom"}

# ------------------------------------------------------------------ verification
CHEXBERT_DEVICE = os.environ.get("TRUSTMED_CHEXBERT_DEVICE", "cpu")
DENSENET_WEIGHTS = os.environ.get("TRUSTMED_DENSENET", "densenet121-res224-all")

# verdict thresholds; per-finding overrides come from calibration.json (guardrail G3)
POSITIVE_THRESHOLD = float(os.environ.get("TRUSTMED_POS", "0.70"))
UNCERTAIN_FLOOR = float(os.environ.get("TRUSTMED_UNCERTAIN", "0.30"))
OMISSION_THRESHOLD = float(os.environ.get("TRUSTMED_OMISSION", "0.90"))
OMISSION_MIN_PPV = float(os.environ.get("TRUSTMED_OMISSION_PPV", "0.50"))

DEFAULT_THRESHOLD = float(os.environ.get("TRUSTMED_DEFAULT_THRESHOLD", "0.55"))
MIN_FINDINGS_FOR_AUTO_ACCEPT = int(os.environ.get("TRUSTMED_MIN_FINDINGS", "3"))


def ensure_dirs() -> None:
    for directory in (DATA_DIR, IMAGE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
