"""SQLite persistence for TrustMed.

Deliberately plain sqlite3: one file, WAL, foreign keys on. Every call opens and
closes its own connection, which is safe under FastAPI's threadpool and keeps
the prototype free of ORM/state surprises.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from . import config

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('clinician', 'radiologist')),
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS images (
    id           TEXT PRIMARY KEY,            -- sha256 of the uploaded bytes
    filename     TEXT,
    content_type TEXT,
    modality     TEXT,
    width        INTEGER,
    height       INTEGER,
    meta_json    TEXT,
    stored_path  TEXT NOT NULL,               -- original bytes (DICOM/JPEG/PNG)
    gray_path    TEXT NOT NULL,               -- 8-bit windowed copy for the verifier
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id     TEXT NOT NULL REFERENCES images(id),
    user_id      INTEGER REFERENCES users(id),
    model        TEXT NOT NULL,
    model_version TEXT,
    prompt_hash  TEXT,
    temperature  REAL,
    seed         INTEGER,
    text         TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('auto_accepted', 'review_suggested', 'review_required')),
    confidence   REAL NOT NULL,
    latency_ms   INTEGER,
    thresholds_json TEXT,
    created_at   TEXT NOT NULL,
    reviewed_at  TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id  INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    label      TEXT NOT NULL,
    polarity   INTEGER NOT NULL,              -- +1 positive, -1 negative, 0 not mentioned
    severity   INTEGER NOT NULL DEFAULT 1,
    sentence   TEXT,
    span_start INTEGER,
    span_end   INTEGER,
    image_prob REAL,
    verdict    TEXT NOT NULL,                 -- supported|uncertain|unsupported|contradiction|omission|not_assessable
    reason     TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id  INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    reviewer_id INTEGER REFERENCES users(id),
    action      TEXT NOT NULL CHECK (action IN ('accept', 'edit', 'reject')),
    comment     TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER,
    entity     TEXT,
    entity_id  TEXT,
    action     TEXT,
    detail     TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
    name          TEXT PRIMARY KEY,
    version       TEXT,
    weights_sha256 TEXT,
    loaded_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_image  ON reports(image_id);
CREATE INDEX IF NOT EXISTS idx_findings_report ON findings(report_id);
CREATE INDEX IF NOT EXISTS idx_reviews_finding ON reviews(finding_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init() -> None:
    config.ensure_dirs()
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def query(sql: str, args: Iterable[Any] = ()) -> list[sqlite3.Row]:
    conn = connect()
    try:
        return list(conn.execute(sql, tuple(args)))
    finally:
        conn.close()


def one(sql: str, args: Iterable[Any] = ()) -> sqlite3.Row | None:
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql: str, args: Iterable[Any] = ()) -> int:
    conn = connect()
    try:
        cur = conn.execute(sql, tuple(args))
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def executemany(sql: str, rows: list[tuple]) -> None:
    conn = connect()
    try:
        conn.executemany(sql, rows)
        conn.commit()
    finally:
        conn.close()


def audit(actor_id: int | None, entity: str, entity_id: str, action: str, detail: Any = None) -> None:
    execute(
        "INSERT INTO audit_log (actor_id, entity, entity_id, action, detail, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (
            actor_id,
            entity,
            entity_id,
            action,
            json.dumps(detail, ensure_ascii=False) if detail is not None else None,
            now(),
        ),
    )
