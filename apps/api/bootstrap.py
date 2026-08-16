"""Ensure repo root and package directories are importable.

The existing MoneyPrinterTurbo engine lives in ``app/`` at the repository
root. The SaaS layer lives in ``apps/`` and ``packages/``. This bootstrap
adds those paths without moving or rewriting the engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EXTRA_PATHS = [
    REPO_ROOT,
    REPO_ROOT / "apps" / "api",
    REPO_ROOT / "packages" / "shared",
    REPO_ROOT / "packages" / "video-engine",
    REPO_ROOT / "packages" / "ai-engine",
    REPO_ROOT / "packages" / "media-engine",
    REPO_ROOT / "packages" / "audio-engine",
]


def ensure_sys_path() -> Path:
    for extra in EXTRA_PATHS:
        path_str = str(extra)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    return REPO_ROOT


ensure_sys_path()
