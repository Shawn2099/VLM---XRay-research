"""HTTP service for google/medgemma-1.5-4b-it on a single CUDA GPU.

The model is a Gemma 3 4B medical multimodal LLM.  Images and DICOM are decoded
with the same code as the CXR-LLaVA service, then passed to the model's chat
template as a PIL image.  The API contract is identical so the UI and test
harness work unchanged.
"""

from __future__ import annotations

import asyncio
import hmac
import io
import logging
import os
import re
import time
from contextlib import asynccontextmanager

import numpy as np
import pydicom
import torch
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_DIR = os.environ.get("MODEL_DIR", "/models/medgemma-1.5-4b-it")
MODEL_ID = "google/medgemma-1.5-4b-it"
UI_PATH = os.environ.get("UI_PATH", "/opt/medgemma/ui.html")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "40"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_BODY_BYTES = MAX_UPLOAD_BYTES + 2 * 1024 * 1024  # multipart overhead
MAX_PIXELS = int(os.environ.get("MAX_PIXELS", "40000000"))
API_KEY = os.environ.get("CXR_API_KEY", "").strip()
ENABLE_DOCS = os.environ.get("CXR_ENABLE_DOCS", "0") == "1"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CXR_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
HEADER_SAFE = re.compile(r"[^A-Za-z0-9 _./+()-]")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("medgemma")

_model = None
_processor = None
_lock = asyncio.Lock()


def _load_model() -> None:
    global _model, _processor

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available inside the container. Start it with --gpus all."
        )

    log.info("loading model from %s", MODEL_DIR)
    started = time.time()
    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_DIR, torch_dtype=torch.bfloat16, attn_implementation="sdpa"
    )
    model = model.to("cuda")
    model.eval()
    torch.set_grad_enabled(False)
    _processor = processor
    _model = model
    log.info(
        "model ready in %.1fs (device=%s, dtype=%s, vram=%.2f GiB)",
        time.time() - started,
        model.device,
        next(model.parameters()).dtype,
        torch.cuda.memory_allocated() / 2**30,
    )


REPORT_PROMPT = (
    "You are an expert radiologist. Analyze this chest X-ray and write a "
    "structured report.\n\n"
    "Findings: describe the lungs, pleura, heart, mediastinum and bones. "
    "Explicitly state whether atelectasis, cardiomegaly, consolidation, "
    "pulmonary edema, pleural effusion or pneumothorax is present.\n"
    "Impression: one or two sentences summarising the important findings."
)
DIFFERENTIAL_PROMPT = (
    "What are the possible differential diagnoses for this patient? "
    "Give a short list, most likely first, with the imaging feature that "
    "supports each one."
)


def _generate(
    image: Image.Image,
    prompt: str,
    temperature: float = 0.0,
    top_p: float = 1.0,
    max_new_tokens: int = 512,
    system: str = "You are an expert radiologist. Answer concisely.",
) -> str:
    image = image.convert("RGB")
    width, height = image.size
    longest = max(width, height)
    if longest > 1024:
        scale = 1024 / longest
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.LANCZOS,
        )

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        },
    ]
    inputs = _processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    # BatchFeature.to() would cast int64 ids too; cast only the floating tensors.
    inputs = {
        key: (value.to("cuda") if torch.is_tensor(value) else value)
        for key, value in inputs.items()
    }
    if "pixel_values" in inputs:
        inputs["pixel_values"] = inputs["pixel_values"].to(torch.bfloat16)
    input_length = inputs["input_ids"].shape[-1]

    do_sample = temperature > 0.001
    kwargs: dict = {"max_new_tokens": max_new_tokens, "do_sample": do_sample}
    if do_sample:
        kwargs.update(temperature=temperature, top_p=top_p)
    with torch.inference_mode():
        output = _model.generate(**inputs, **kwargs)

    decode = getattr(_processor, "decode", None) or _processor.tokenizer.decode
    text = decode(output[0][input_length:], skip_special_tokens=True)
    # MedGemma 1.5 may emit an optional thinking block; reports do not need it.
    text = re.sub(r"<unused94>thought.*?<unused95>", "", text, flags=re.S)
    return text.strip()


def _report(image: Image.Image, temperature: float, top_p: float) -> str:
    return _generate(
        image,
        REPORT_PROMPT,
        temperature,
        top_p,
        system=(
            "You are an expert radiologist. Answer with a single structured "
            "report. Do not add commentary."
        ),
    )


def _differential(image: Image.Image, temperature: float, top_p: float) -> str:
    return _generate(image, DIFFERENTIAL_PROMPT, temperature, top_p)


def _ask(question: str, image: Image.Image, temperature: float, top_p: float) -> str:
    yes_no = bool(
        re.match(r"\s*(is|are|does|do|has|have|was|were|can)\b", question, re.I)
    )
    if yes_no:
        instruction = (
            'Answer with exactly one word, "Yes" or "No", then one sentence '
            "of justification."
        )
    else:
        instruction = "Answer in one or two sentences."
    prompt = f"{instruction}\nQuestion: {question}"
    return _generate(
        image,
        prompt,
        temperature,
        top_p,
        max_new_tokens=256,
        system="You are an expert radiologist. Answer the question directly.",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    _load_model()
    yield
    torch.cuda.empty_cache()


app = FastAPI(
    title="MedGemma 1.5 4B — chest X-ray",
    version="1.0",
    description="Chest X-ray report generation (research use only).",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Image-Source",
        "X-Image-Width",
        "X-Image-Height",
        "X-Dicom-Modality",
        "X-Dicom-Photometric",
        "X-Dicom-BitsStored",
        "X-Dicom-Window",
    ],
)


@app.middleware("http")
async def reject_oversized_body(request: Request, call_next):
    """Reject an oversized upload before Starlette buffers the form."""
    if request.method in {"POST", "PUT"}:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": f"file larger than {MAX_UPLOAD_MB} MB"},
            )
    return await call_next(request)


def require_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not API_KEY:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


def _check_sampling(temperature: float, top_p: float) -> None:
    if not 0.0 <= temperature <= 2.0:
        raise HTTPException(status_code=422, detail="temperature must be 0..2")
    if not 0.0 < top_p <= 1.0:
        raise HTTPException(status_code=422, detail="top_p must be in (0, 1]")


async def _read_upload(file: UploadFile) -> bytes:
    # Read at most one byte past the limit; never buffer an unbounded body.
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"file larger than {MAX_UPLOAD_MB} MB"
        )
    return raw


def _pil_image(raw: bytes) -> tuple[Image.Image, dict]:
    try:
        image = Image.open(io.BytesIO(raw))
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="not a readable image")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"cannot decode image: {exc}")

    # Check dimensions BEFORE any transpose/copy/load decodes pixel data.
    if image.width * image.height > MAX_PIXELS:
        raise HTTPException(status_code=413, detail="image resolution too large")

    try:
        image = ImageOps.exif_transpose(image)  # honour phone/camera orientation
        image.load()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"cannot decode image: {exc}")

    # The model raises on 16-bit input; reject it with a useful message instead
    # of letting a silent 8-bit conversion clip the data.
    if image.mode in {"I", "I;16", "I;16B", "I;16L", "I;16N", "F"}:
        raise HTTPException(
            status_code=422,
            detail=(
                "16-bit images are not supported; send the DICOM "
                "file instead (it will be windowed to 8-bit), or export an "
                "8-bit grayscale image"
            ),
        )
    return image, {
        "source": "image",
        "mode": image.mode,
        "width": image.width,
        "height": image.height,
        "bytes": len(raw),
    }


def _first_float(value) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) or type(value).__name__ == "MultiValue":
            value = value[0]
        return float(value)
    except Exception:
        return None


def _safe_header(value, limit: int = 80) -> str:
    """DICOM tag values are file-controlled; keep them header-safe."""
    return HEADER_SAFE.sub("", str(value))[:limit]


def _dicom_image(raw: bytes, force: bool = False) -> tuple[Image.Image, dict]:
    try:
        ds = pydicom.dcmread(io.BytesIO(raw), force=force)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"not a readable DICOM file: {exc}")

    if not hasattr(ds, "PixelData"):
        raise HTTPException(status_code=422, detail="DICOM file has no pixel data")

    samples = int(getattr(ds, "SamplesPerPixel", 1) or 1)
    if samples != 1:
        raise HTTPException(
            status_code=422,
            detail="only single-channel grayscale DICOM is supported",
        )

    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    if frames != 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "multi-frame DICOM is not supported; export a single-frame "
                "frontal or lateral image"
            ),
        )

    bits_allocated = int(getattr(ds, "BitsAllocated", 16) or 16)
    if bits_allocated > 16:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported BitsAllocated={bits_allocated}; 8/16-bit required",
        )

    try:
        rows = int(ds.Rows)
        columns = int(ds.Columns)
    except Exception:
        raise HTTPException(status_code=422, detail="DICOM is missing Rows/Columns")

    if rows <= 0 or columns <= 0 or rows * columns > MAX_PIXELS:
        raise HTTPException(status_code=413, detail="DICOM resolution too large")

    photometric = str(getattr(ds, "PhotometricInterpretation", "") or "").upper()
    modality = str(getattr(ds, "Modality", "") or "")
    bits_stored = int(getattr(ds, "BitsStored", 0) or 0)
    centre = _first_float(getattr(ds, "WindowCenter", None))
    width = _first_float(getattr(ds, "WindowWidth", None))

    try:
        array = np.asarray(ds.pixel_array)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"cannot decode DICOM pixel data: {exc}"
        )

    if array.ndim == 3 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported DICOM pixel shape {array.shape}",
        )

    work = np.asarray(array, dtype=np.float64)
    try:
        work = np.asarray(apply_modality_lut(work, ds), dtype=np.float64)
    except Exception:
        pass

    # pydicom's apply_voi_lut() returns the array unchanged (without raising)
    # when no VOI elements exist, so decide from the tags, not from a try/except.
    has_voi = bool(getattr(ds, "VOILUTSequence", None))
    if centre is not None and width is not None and width > 0:
        has_voi = True

    voi_applied = False
    if has_voi:
        try:
            work = np.asarray(apply_voi_lut(work, ds, index=0), dtype=np.float64)
            voi_applied = True
        except Exception:
            pass

    finite = work[np.isfinite(work)]
    if finite.size == 0:
        raise HTTPException(status_code=422, detail="DICOM pixel data is empty")

    if voi_applied:
        low, high = float(finite.min()), float(finite.max())
    else:
        # No usable VOI LUT: robust percentiles, so one burned-in marker does
        # not crush the contrast of the whole image.
        low, high = (float(v) for v in np.percentile(finite, [1, 99]))
    if high <= low:
        low, high = float(finite.min()), float(finite.max())
    if high <= low:
        high = low + 1.0

    scaled = np.clip((work - low) / (high - low), 0.0, 1.0)
    if photometric == "MONOCHROME1":
        # Minimum sample value is meant to be displayed as white.
        scaled = 1.0 - scaled

    image = Image.fromarray(np.round(scaled * 255.0).astype(np.uint8), mode="L")
    return image, {
        "source": "dicom",
        "mode": "L",
        "width": image.width,
        "height": image.height,
        "bytes": len(raw),
        "modality": _safe_header(modality),
        "photometric": _safe_header(photometric),
        "bits_stored": bits_stored,
        "frames": frames,
        "window": _safe_header(f"{centre:g}/{width:g}") if centre and width else "",
        "voi_applied": voi_applied,
    }


def _has_dicom_magic(raw: bytes) -> bool:
    return len(raw) >= 132 and raw[128:132] == b"DICM"


async def _load_image(file: UploadFile) -> tuple[Image.Image, dict]:
    raw = await _read_upload(file)
    name = (file.filename or "").lower()

    if name.endswith((".dcm", ".dicom")) or _has_dicom_magic(raw):
        try:
            return _dicom_image(raw)
        except HTTPException as dicom_error:
            # Valid DICOM without the 128-byte preamble/DICM magic needs force.
            try:
                return _dicom_image(raw, force=True)
            except HTTPException:
                raise dicom_error

    try:
        return _pil_image(raw)
    except HTTPException as image_error:
        # Some DICOM files have no preamble; try a forced parse as a fallback.
        try:
            return _dicom_image(raw, force=True)
        except HTTPException:
            raise image_error


async def _infer(fn, *args) -> tuple[str, float]:
    """Run one inference at a time; the model is not re-entrant."""
    started = time.time()
    async with _lock:
        try:
            text = await asyncio.to_thread(fn, *args)
        except Exception:
            log.exception("inference failed")
            raise HTTPException(
                status_code=500, detail="inference failed; check server logs"
            )
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=502, detail="model produced an empty response")
    return cleaned, time.time() - started


@app.get("/", include_in_schema=False)
def index():
    if os.path.isfile(UI_PATH):
        return FileResponse(UI_PATH, media_type="text/html")
    return {
        "model": MODEL_ID,
        "endpoints": ["/report", "/differential", "/ask", "/preview", "/health"],
        "note": "research use only; not for clinical decisions",
    }


@app.get("/config")
def config() -> dict:
    return {
        "model": MODEL_ID,
        "auth_required": bool(API_KEY),
        "max_upload_mb": MAX_UPLOAD_MB,
        "modes": ["report", "differential", "ask"],
    }


@app.get("/health")
def health() -> dict:
    if _model is None:
        return {"status": "loading"}
    return {
        "status": "ok",
        "device": str(_model.device),
        "gpu": torch.cuda.get_device_name(0),
        "vram_allocated_gib": round(torch.cuda.memory_allocated() / 2**30, 2),
        "vram_reserved_gib": round(torch.cuda.memory_reserved() / 2**30, 2),
    }


@app.post("/preview")
async def preview(
    file: UploadFile = File(...),
    _: None = Depends(require_key),
) -> Response:
    image, meta = await _load_image(file)
    buffer = io.BytesIO()
    image.convert("L").save(buffer, format="PNG")
    headers = {
        "X-Image-Source": _safe_header(meta.get("source", "image")),
        "X-Image-Width": str(image.width),
        "X-Image-Height": str(image.height),
        "X-Image-Mode": _safe_header(image.mode),
    }
    for key, header in (
        ("modality", "X-Dicom-Modality"),
        ("photometric", "X-Dicom-Photometric"),
        ("bits_stored", "X-Dicom-BitsStored"),
        ("window", "X-Dicom-Window"),
    ):
        value = meta.get(key)
        if value not in (None, ""):
            headers[header] = _safe_header(value)
    return Response(content=buffer.getvalue(), media_type="image/png", headers=headers)


@app.post("/report")
async def report(
    file: UploadFile = File(...),
    temperature: float = Form(0.2),
    top_p: float = Form(0.8),
    _: None = Depends(require_key),
) -> dict:
    _check_sampling(temperature, top_p)
    image, meta = await _load_image(file)
    text, latency = await _infer(
        _report, image, temperature, top_p
    )
    log.info(
        "report source=%s bytes=%d latency=%.1fs",
        meta.get("source"),
        meta.get("bytes", 0),
        latency,
    )
    return {
        "mode": "report",
        "report": text,
        "latency_s": round(latency, 2),
        "model": MODEL_ID,
        "source": meta.get("source"),
    }


@app.post("/differential")
async def differential(
    file: UploadFile = File(...),
    temperature: float = Form(0.2),
    top_p: float = Form(0.8),
    _: None = Depends(require_key),
) -> dict:
    _check_sampling(temperature, top_p)
    image, meta = await _load_image(file)
    text, latency = await _infer(
        _differential, image, temperature, top_p
    )
    log.info(
        "differential source=%s bytes=%d latency=%.1fs",
        meta.get("source"),
        meta.get("bytes", 0),
        latency,
    )
    return {
        "mode": "differential",
        "differential": text,
        "latency_s": round(latency, 2),
        "model": MODEL_ID,
        "source": meta.get("source"),
    }


@app.post("/ask")
async def ask(
    file: UploadFile = File(...),
    question: str = Form(...),
    temperature: float = Form(0.2),
    top_p: float = Form(0.8),
    _: None = Depends(require_key),
) -> dict:
    _check_sampling(temperature, top_p)
    if not question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")
    if len(question) > 2000:
        raise HTTPException(status_code=422, detail="question too long (max 2000 chars)")
    image, meta = await _load_image(file)
    text, latency = await _infer(
        _ask, question.strip(), image, temperature, top_p
    )
    log.info(
        "ask source=%s bytes=%d latency=%.1fs",
        meta.get("source"),
        meta.get("bytes", 0),
        latency,
    )
    return {
        "mode": "ask",
        "question": question.strip(),
        "answer": text,
        "latency_s": round(latency, 2),
        "model": MODEL_ID,
        "source": meta.get("source"),
    }
