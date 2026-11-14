"""One report request: generate -> extract -> verify -> score -> persist."""

from __future__ import annotations

import hashlib
import json

from .. import config, db
from . import classifier, confidence, findings, generator, ingest, verdict


class UnknownImage(LookupError):
    """The image id does not exist."""


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def analyze(image_id: str, user_id: int | None, threshold: float) -> dict:
    image = db.one("SELECT * FROM images WHERE id = ?", (image_id,))
    if image is None:
        raise UnknownImage(image_id)

    text, latency_ms = generator.generate(image["stored_path"], image["content_type"] or "")

    extracted = findings.extract(text)
    probs = classifier.predict(image["gray_path"])
    rows = verdict.apply(extracted, probs)

    meta = json.loads(image["meta_json"] or "{}")
    if "view" not in meta:
        from PIL import Image as PILImage

        with PILImage.open(image["gray_path"]) as stored_image:
            meta.update(ingest.view_check(stored_image))
    view = meta.get("view", "unknown")
    if view == "likely_lateral":
        # A lateral projection cannot be verified by a frontal-trained model:
        # refuse rather than emit meaningless probabilities.
        for row in rows:
            row["verdict"] = "not_assessable"
            row["image_prob"] = None
            row["reason"] = "image looks lateral; frontal verification disabled"

    confidence_value = confidence.score(rows)
    status = confidence.status(confidence_value, rows, threshold)
    if view == "likely_lateral":
        status = "review_required"

    report_id = db.execute(
        "INSERT INTO reports (image_id, user_id, model, model_version, prompt_hash, temperature, "
        "seed, text, status, confidence, latency_ms, thresholds_json, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            image_id,
            user_id,
            config.BACKEND_NAME,
            "v1.5",
            _prompt_hash("report"),
            0.0,
            0,
            text,
            status,
            confidence_value,
            latency_ms,
            json.dumps(verdict.thresholds(), sort_keys=True),
            db.now(),
        ),
    )

    for row in rows:
        row["id"] = db.execute(
            "INSERT INTO findings (report_id, label, polarity, severity, sentence, span_start, "
            "span_end, image_prob, verdict, reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                report_id,
                row["label"],
                row["polarity"],
                row["severity"],
                row["sentence"],
                row["span_start"],
                row["span_end"],
                row["image_prob"],
                row["verdict"],
                row["reason"],
            ),
        )

    db.audit(user_id, "report", str(report_id), "generate",
             {"image_id": image_id, "status": status, "confidence": confidence_value})

    return {
        "report_id": report_id,
        "text": text,
        "status": status,
        "confidence": confidence_value,
        "latency_ms": latency_ms,
        "model": config.BACKEND_NAME,
        "view": view,
        "symmetry": meta.get("symmetry"),
        "findings": rows,
        "probabilities": probs,
    }
