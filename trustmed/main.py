"""TrustMed web app."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import auth, config, db
from .services import classifier, findings, generator, ingest, pipeline, verdict

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    auth.seed_admin()
    yield


app = FastAPI(
    title="TrustMed", version=APP_VERSION, docs_url=None, redoc_url=None, lifespan=lifespan
)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


# ------------------------------------------------------------------ pages
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "user": user,
            "threshold": config.DEFAULT_THRESHOLD,
            "backend": config.BACKEND_NAME,
        },
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": ""})


@app.post("/auth/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = auth.authenticate(email, password)
    if user is None:
        return templates.TemplateResponse(
            request, "login.html", {"error": "wrong email or password"}, status_code=401
        )
    db.audit(user["id"], "user", str(user["id"]), "login", None)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        config.COOKIE_NAME,
        auth.issue_session(user["id"]),
        httponly=True,
        samesite="lax",
        max_age=config.SESSION_HOURS * 3600,
    )
    return response


@app.post("/auth/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(config.COOKIE_NAME)
    return response


# ------------------------------------------------------------------ api
@app.get("/health")
def health():
    backend = generator.info()
    full, advisory = verdict.gate()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "backend": backend,
        "verifier": classifier.self_test(),
        "gate": {
            "verified": sorted(full),
            "advisory": sorted(advisory),
            "calibrated": config.CALIBRATION_PATH.is_file(),
        },
    }


@app.get("/api/selftest")
def selftest(request: Request):
    auth.require_user(request)
    return {"chexbert": findings.self_test(), "classifier": classifier.self_test()}


@app.post("/api/upload")
def upload(request: Request, file: UploadFile = File(...)):
    user = auth.require_user(request)
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in config.ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="upload a JPEG, PNG or DICOM file")

    try:
        stored = ingest.store(raw, file.filename or "upload", file.content_type or "")
    except ingest.UploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    db.audit(user["id"], "image", stored["id"], "upload", {"filename": file.filename})
    return {
        "image_id": stored["id"],
        "width": stored["meta"]["width"],
        "height": stored["meta"]["height"],
        "source": stored["meta"].get("source"),
        "window": stored["meta"].get("window", ""),
    }


@app.post("/api/report")
def report(
    request: Request,
    image_id: str = Form(...),
    threshold: float = Form(config.DEFAULT_THRESHOLD),
):
    user = auth.require_user(request)
    try:
        result = pipeline.analyze(image_id, user["id"], threshold)
    except generator.BackendError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except pipeline.UnknownImage:
        raise HTTPException(status_code=404, detail="unknown image")
    except Exception as exc:                       # noqa: BLE001 - report the cause
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    return JSONResponse(result)


@app.get("/api/reports/{report_id}")
def get_report(request: Request, report_id: int):
    auth.require_user(request)
    row = db.one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    rows = db.query("SELECT * FROM findings WHERE report_id = ? ORDER BY severity DESC", (report_id,))
    return {"report": dict(row), "findings": [dict(r) for r in rows]}


@app.post("/api/findings/{finding_id}/review")
def review(
    request: Request,
    finding_id: int,
    action: str = Form(...),
    comment: str = Form(""),
):
    user = auth.require_radiologist(request)
    if action not in {"accept", "edit", "reject"}:
        raise HTTPException(status_code=422, detail="action must be accept, edit or reject")
    row = db.one("SELECT report_id FROM findings WHERE id = ?", (finding_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="finding not found")

    db.execute(
        "INSERT INTO reviews (finding_id, reviewer_id, action, comment, created_at) VALUES (?,?,?,?,?)",
        (finding_id, user["id"], action, comment, db.now()),
    )
    db.execute("UPDATE reports SET reviewed_at = ? WHERE id = ?", (db.now(), row["report_id"]))
    db.audit(user["id"], "finding", str(finding_id), f"review_{action}", {"comment": comment})
    return {"ok": True}


@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    user = auth.current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    rows = db.query(
        "SELECT r.id, r.status, r.confidence, r.created_at, i.filename "
        "FROM reports r JOIN images i ON i.id = r.image_id "
        "ORDER BY r.id DESC LIMIT 100"
    )
    return templates.TemplateResponse(
        request, "history.html", {"user": user, "reports": [dict(r) for r in rows]}
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return HTMLResponse(f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>", status_code=exc.status_code)
