"""Safe filename and object-key helpers. Blocks path traversal."""

from __future__ import annotations

import re
from pathlib import Path

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str, fallback: str = "upload.bin") -> str:
    raw = (name or "").replace("\\", "/").split("/")[-1].strip()
    raw = raw.lstrip(".")
    if not raw or raw in {".", ".."}:
        return fallback
    cleaned = _UNSAFE.sub("_", raw)
    cleaned = cleaned.strip("._") or fallback
    return cleaned[:180]


def safe_object_key(key: str) -> str:
    parts = [part for part in (key or "").replace("\\", "/").split("/") if part not in {"", ".", ".."}]
    if not parts:
        raise ValueError("empty object key")
    cleaned = [safe_filename(part, fallback="object") for part in parts]
    return "/".join(cleaned)


def is_allowed_upload(filename: str, allowed_suffixes: set[str]) -> bool:
    suffix = Path(filename).suffix.lower()
    return suffix in allowed_suffixes
