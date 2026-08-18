"""Safe provider polling: backoff, timeout, no infinite loops."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def poll_settings() -> tuple[float, float, float]:
    initial = float(os.getenv("AI_VIDEO_POLL_INITIAL_SECONDS") or 10)
    maximum = float(os.getenv("AI_VIDEO_POLL_MAX_SECONDS") or 60)
    wait = float(os.getenv("AI_VIDEO_MAX_WAIT_SECONDS") or 900)
    return max(1.0, initial), max(initial, maximum), max(30.0, wait)


def poll_until(
    fetch: Callable[[], T],
    *,
    is_done: Callable[[T], bool],
    is_failed: Callable[[T], bool],
    should_cancel: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    initial, maximum, limit = poll_settings()
    delay = initial
    started = clock()
    last = fetch()
    while True:
        if should_cancel and should_cancel():
            return last
        if is_done(last) or is_failed(last):
            return last
        if clock() - started >= limit:
            raise TimeoutError("AI provider polling exceeded AI_VIDEO_MAX_WAIT_SECONDS")
        sleep(delay)
        delay = min(maximum, delay * 1.5)
        last = fetch()
