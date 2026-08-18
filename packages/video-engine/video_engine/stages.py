"""Job stages and progress percentages for the SaaS worker.

Progress is tied to real pipeline stages, not a timer.
"""

from __future__ import annotations

GENERATION_STAGES: dict[str, int] = {
    "QUEUED": 0,
    "ANALYZING": 10,
    "GENERATING_SCRIPT": 20,
    "PLANNING": 18,
    "FETCHING_MEDIA": 35,
    "GENERATING_AUDIO": 50,
    "GENERATING_SUBTITLES": 65,
    "RENDERING": 80,
    "UPLOADING": 95,
    "COMPLETED": 100,
    "FAILED": 0,
    "CANCELLED": 0,
}


def stage_progress(stage: str) -> int:
    return GENERATION_STAGES.get(stage, 0)
