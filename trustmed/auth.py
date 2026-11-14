"""Password hashing and signed-cookie sessions (stdlib only)."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

from fastapi import HTTPException, Request

from . import config, db

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(digest_hex)),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


# ------------------------------------------------------------------ users
def create_user(email: str, password: str, role: str = "clinician", is_admin: bool = False) -> int:
    email = email.strip().lower()
    if role not in {"clinician", "radiologist"}:
        raise ValueError("role must be clinician or radiologist")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    return db.execute(
        "INSERT INTO users (email, password_hash, role, is_admin, created_at) VALUES (?,?,?,?,?)",
        (email, hash_password(password), role, int(is_admin), db.now()),
    )


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    row = db.one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def seed_admin() -> None:
    if db.one("SELECT id FROM users WHERE is_admin = 1"):
        return
    user_id = create_user(config.ADMIN_EMAIL, config.ADMIN_PASSWORD, "radiologist", is_admin=True)
    db.audit(user_id, "user", str(user_id), "seed_admin", {"email": config.ADMIN_EMAIL})


# ------------------------------------------------------------------ sessions
def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session(user_id: int) -> str:
    expires = int(time.time()) + config.SESSION_HOURS * 3600
    payload = f"{user_id}.{expires}"
    return f"{payload}.{_sign(payload)}"


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        user_id, expires, signature = token.rsplit(".", 2)
        payload = f"{user_id}.{expires}"
        if not hmac.compare_digest(_sign(payload), signature):
            return None
        if int(expires) < int(time.time()):
            return None
        return int(user_id)
    except Exception:
        return None


def current_user(request: Request) -> dict[str, Any] | None:
    user_id = read_session(request.cookies.get(config.COOKIE_NAME))
    if user_id is None:
        return None
    row = db.one("SELECT id, email, role, is_admin FROM users WHERE id = ?", (user_id,))
    return dict(row) if row else None


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="sign in required")
    return user


def require_radiologist(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "radiologist" and not user["is_admin"]:
        raise HTTPException(status_code=403, detail="radiologist role required")
    return user
