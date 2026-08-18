from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai_engine.types import GenerationHandle, GenerationStatus, ProviderCapabilities

_API = "https://api.replicate.com/v1"
_ALLOWED_HOSTS = {"replicate.delivery", "pbxt.replicate.delivery", "tjzk.replicate.delivery"}


class ReplicateImageProvider:
    name = "replicate"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("AI_IMAGE_API_KEY") or os.getenv("AI_VIDEO_API_KEY") or os.getenv("REPLICATE_API_TOKEN") or "").strip()
        self.model = (model or os.getenv("AI_IMAGE_MODEL") or "black-forest-labs/flux-schnell").strip()

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            models=[self.model],
            aspect_ratios=["9:16", "16:9", "1:1"],
            durations=[0],
            supports_negative_prompt=True,
            production=True,
        )

    def generate_image(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        model: str | None = None,
        negative_prompt: str | None = None,
    ) -> GenerationHandle:
        chosen = (model or self.model).strip()
        owner, name = chosen.split("/", 1)
        payload = {"input": {"prompt": prompt, "aspect_ratio": aspect_ratio}}
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt
        data = self._request("POST", f"{_API}/models/{owner}/{name}/predictions", json=payload)
        return self._to_handle(data)

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle:
        return self._to_handle(self._request("GET", f"{_API}/predictions/{provider_job_id}"))

    def download_result(self, provider_job_id: str, destination: str) -> str:
        handle = self.get_generation_status(provider_job_id)
        if handle.status != GenerationStatus.COMPLETED or not handle.result_url:
            raise RuntimeError(handle.error or "replicate image is not ready")
        host = (urlparse(handle.result_url).hostname or "").lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in _ALLOWED_HOSTS):
            raise RuntimeError("refusing to download a result from an untrusted host")
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(handle.result_url, stream=True, timeout=120) as response:
            response.raise_for_status()
            path.write_bytes(response.content)
        return str(path)

    def _request(self, method: str, url: str, **kwargs):
        if not self.api_key:
            raise RuntimeError("AI_IMAGE_API_KEY is not configured")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"replicate HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    def _to_handle(self, data: dict) -> GenerationHandle:
        status = str(data.get("status") or "").lower()
        mapped = {
            "starting": GenerationStatus.QUEUED,
            "processing": GenerationStatus.PROCESSING,
            "succeeded": GenerationStatus.COMPLETED,
            "failed": GenerationStatus.FAILED,
            "canceled": GenerationStatus.CANCELLED,
        }.get(status, GenerationStatus.PROCESSING)
        output = data.get("output")
        result = output[-1] if isinstance(output, list) and output else (output if isinstance(output, str) else None)
        return GenerationHandle(
            provider=self.name,
            provider_job_id=str(data.get("id") or ""),
            status=mapped,
            progress=100 if mapped is GenerationStatus.COMPLETED else 40,
            result_url=result,
            error=str(data.get("error") or "") or None,
        )
