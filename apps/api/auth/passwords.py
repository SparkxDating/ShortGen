"""Password hashing using bcrypt. Never store plaintext passwords."""

from __future__ import annotations

import os

import bcrypt

_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    payload = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    rounds = 4 if os.getenv("ENVIRONMENT", "").lower() == "test" else 12
    return bcrypt.hashpw(payload, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    payload = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(payload, password_hash.encode("utf-8"))
    except ValueError:
        return False
