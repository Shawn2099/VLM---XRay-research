"""Image ingest: DICOM windowing, 16-bit rejection, colour-photo rejection.

Logic carried over from the validated `deploy/app.py` loader (49/49 + 58/58
checks); it raises ValueError instead of HTTPException so it stays testable.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from pydicom import dcmread
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut

from .. import config, db


class UploadError(ValueError):
    """Bad input; the message is safe to show the user."""


def _first_float(value):
    try:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) or type(value).__name__ == "MultiValue":
            value = value[0]
        return float(value)
    except Exception:
        return None


def _dicom(raw: bytes) -> tuple[Image.Image, dict]:
    try:
        ds = dcmread(io.BytesIO(raw), force=False)
    except Exception as exc:
        raise UploadError(f"not a readable DICOM file: {exc}")

    if not hasattr(ds, "PixelData"):
        raise UploadError("DICOM file has no pixel data")
    if int(getattr(ds, "SamplesPerPixel", 1) or 1) != 1:
        raise UploadError("only single-channel grayscale DICOM is supported")
    if int(getattr(ds, "NumberOfFrames", 1) or 1) != 1:
        raise UploadError("multi-frame DICOM is not supported")
    if int(getattr(ds, "BitsAllocated", 16) or 16) > 16:
        raise UploadError("unsupported bits allocated; 8/16-bit required")

    rows, columns = int(ds.Rows), int(ds.Columns)
    if rows <= 0 or columns <= 0 or rows * columns > config.MAX_PIXELS:
        raise UploadError("DICOM resolution too large")

    photometric = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    centre = _first_float(getattr(ds, "WindowCenter", None))
    width = _first_float(getattr(ds, "WindowWidth", None))

    try:
        array = np.asarray(ds.pixel_array)
    except Exception as exc:
        raise UploadError(f"cannot decode DICOM pixel data: {exc}")
    if array.ndim == 3 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2:
        raise UploadError(f"unsupported DICOM pixel shape {array.shape}")

    work = np.asarray(array, dtype=np.float64)
    try:
        work = np.asarray(apply_modality_lut(work, ds), dtype=np.float64)
    except Exception:
        pass

    has_voi = bool(getattr(ds, "VOILUTSequence", None)) or (
        centre is not None and width is not None and width > 0
    )
    voi_applied = False
    if has_voi:
        try:
            work = np.asarray(apply_voi_lut(work, ds, index=0), dtype=np.float64)
            voi_applied = True
        except Exception:
            pass

    finite = work[np.isfinite(work)]
    if finite.size == 0:
        raise UploadError("DICOM pixel data is empty")

    if voi_applied:
        low, high = float(finite.min()), float(finite.max())
    else:
        low, high = (float(v) for v in np.percentile(finite, [1, 99]))
    if high <= low:
        low, high = float(finite.min()), float(finite.max())
    if high <= low:
        high = low + 1.0

    scaled = np.clip((work - low) / (high - low), 0.0, 1.0)
    if photometric == "MONOCHROME1":
        scaled = 1.0 - scaled          # minimum sample value is displayed white

    image = Image.fromarray(np.round(scaled * 255.0).astype(np.uint8), mode="L")
    return image, {
        "source": "dicom",
        "modality": str(getattr(ds, "Modality", "") or ""),
        "photometric": photometric,
        "bits_stored": int(getattr(ds, "BitsStored", 0) or 0),
        "window": f"{centre:g}/{width:g}" if centre and width else "",
        "voi_applied": voi_applied,
    }


def _plain(raw: bytes) -> tuple[Image.Image, dict]:
    try:
        image = Image.open(io.BytesIO(raw))
    except UnidentifiedImageError:
        raise UploadError("not a readable image")
    except Exception as exc:
        raise UploadError(f"cannot decode image: {exc}")

    if image.width * image.height > config.MAX_PIXELS:
        raise UploadError("image resolution too large")
    if image.mode in {"I", "I;16", "I;16B", "I;16L", "I;16N", "F"}:
        raise UploadError(
            "16-bit images are not supported; send the DICOM file instead so it "
            "can be windowed to 8-bit"
        )

    try:
        image = ImageOps.exif_transpose(image)
        image.load()
    except Exception as exc:
        raise UploadError(f"cannot decode image: {exc}")

    if image.mode != "L":
        rgb = image.convert("RGB")
        array = np.asarray(rgb).astype(np.int16)
        spread = float(np.abs(array[..., 0] - array[..., 1]).mean() +
                       np.abs(array[..., 1] - array[..., 2]).mean())
        if spread > 12:
            raise UploadError("this looks like a colour photo, not a chest radiograph")
        image = rgb.convert("L")

    return image, {"source": "image", "mode": image.mode}


def decode(raw: bytes, filename: str) -> tuple[Image.Image, dict]:
    is_dicom = filename.lower().endswith((".dcm", ".dicom")) or (
        len(raw) >= 132 and raw[128:132] == b"DICM"
    )
    if is_dicom:
        image, meta = _dicom(raw)
    else:
        image, meta = _plain(raw)
    meta.update({"width": image.width, "height": image.height, "bytes": len(raw)})
    return image, meta


def store(raw: bytes, filename: str, content_type: str) -> dict:
    """Decode, persist original + 8-bit grey copy, return the `images` row."""
    image, meta = decode(raw, filename)
    digest = hashlib.sha256(raw).hexdigest()

    suffix = Path(filename or "").suffix.lower() or ".bin"
    original = config.IMAGE_DIR / f"{digest}{suffix}"
    grey = config.IMAGE_DIR / f"{digest}.gray.png"

    if not original.is_file():
        original.write_bytes(raw)
    if not grey.is_file():
        image.save(grey, format="PNG", optimize=True)

    row = db.one("SELECT id FROM images WHERE id = ?", (digest,))
    if row is None:
        db.execute(
            "INSERT INTO images (id, filename, content_type, modality, width, height, "
            "meta_json, stored_path, gray_path, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                digest,
                filename,
                content_type,
                meta.get("source", ""),
                image.width,
                image.height,
                __import__("json").dumps(meta),
                str(original),
                str(grey),
                db.now(),
            ),
        )
    return {
        "id": digest,
        "filename": filename,
        "meta": meta,
        "stored_path": str(original),
        "gray_path": str(grey),
    }
