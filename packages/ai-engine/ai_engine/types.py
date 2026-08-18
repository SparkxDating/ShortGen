"""Shared types for AI visual providers. No renderer lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GenerationStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class GenerationHandle:
    provider: str
    provider_job_id: str
    status: GenerationStatus
    progress: int = 0
    result_url: str | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCapabilities:
    name: str
    models: list[str]
    aspect_ratios: list[str]
    durations: list[int]
    supports_negative_prompt: bool = False
    supports_audio: bool = False
    supports_webhook: bool = False
    production: bool = True
