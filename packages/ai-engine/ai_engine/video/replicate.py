"""Replicate official-model predictions. Documented async HTTP contract.

POST https://api.replicate.com/v1/models/{owner}/{name}/predictions
GET  https://api.replicate.com/v1/predictions/{id}
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from ai_engine.types import GenerationHandle, GenerationStatus, ProviderCapabilities

_API = "https://api.replicate.com/v1"
_ALLOWED_HOSTS = {"replicate.delivery", "pbxt.replicate.delivery", "tjzk.replicate.delivery"}


class ReplicateVideoProvider:
    name = "replicate"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("AI_VIDEO_API_KEY") or os.getenv("REPLICATE_API_TOKEN") or "").strip()
        self.model = (model or os.getenv("AI_VIDEO_MODEL") or "luma/ray-flash-2-720p").strip()

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self.name,
            models=[self.model],
            aspect_ratios=["9:16", "16:9", "1:1"],
            durations=[5, 9, 10],
            supports_negative_prompt=False,
            supports_webhook=True,
            production=True,
        )

    def create_generation(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration: float,
        model: str | None = None,
        negative_prompt: str | None = None,
        webhook_url: str | None = None,
    ) -> GenerationHandle:
        chosen = (model or self.model).strip()
        if "/" not in chosen:
            raise RuntimeError("AI_VIDEO_MODEL must look like owner/name")
        owner, name = chosen.split("/", 1)
        payload: dict = {
            "input": {
                "prompt": prompt,
                "aspect_ratio": self._map_aspect(aspect_ratio),
            }
        }
        if duration:
            payload["input"]["duration"] = int(max(5, min(10, round(duration))))
        if webhook_url:
            payload["webhook"] = webhook_url
            payload["webhook_events_filter"] = ["completed"]
        response = self._request("POST", f"{_API}/models/{owner}/{name}/predictions", json=payload)
        return self._to_handle(response, chosen)

    def get_generation_status(self, provider_job_id: str) -> GenerationHandle:
        response = self._request("GET", f"{_API}/predictions/{provider_job_id}")
        return self._to_handle(response, self.model)

    def download_result(self, provider_job_id: str, destination: str) -> str:
        handle = self.get_generation_status(provider_job_id)
        if handle.status != GenerationStatus.COMPLETED or not handle.result_url:
            raise RuntimeError(handle.error or "replicate video is not ready")
        self._assert_result_url(handle.result_url)
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(handle.result_url, stream=True, timeout=180) as response:
            response.raise_for_status()
            with path.open("wb") as handle_file:
                for chunk in response.iter_content(1024 * 256):
                    if chunk:
                        handle_file.write(chunk)
        return str(path)

    def cancel_generation(self, provider_job_id: str) -> GenerationHandle:
        response = self._request("POST", f"{_API}/predictions/{provider_job_id}/cancel")
        return self._to_handle(response, self.model)

    def _request(self, method: str, url: str, **kwargs):
        if not self.api_key:
            raise RuntimeError("AI_VIDEO_API_KEY is not configured")
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"replicate HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    def _to_handle(self, data: dict, model: str) -> GenerationHandle:
        status = str(data.get("status") or "").lower()
        mapped = {
            "starting": GenerationStatus.QUEUED,
            "processing": GenerationStatus.PROCESSING,
            "succeeded": GenerationStatus.COMPLETED,
            "failed": GenerationStatus.FAILED,
            "canceled": GenerationStatus.CANCELLED,
            "cancelled": GenerationStatus.CANCELLED,
        }.get(status, GenerationStatus.PROCESSING)
        output = data.get("output")
        result = None
        if isinstance(output, str):
            result = output
        elif isinstance(output, list) and output:
            result = str(output[-1])
        elif isinstance(output, dict):
            result = output.get("video") or output.get("url")
        return GenerationHandle(
            provider=self.name,
            provider_job_id=str(data.get("id") or ""),
            status=mapped,
            progress=100 if mapped is GenerationStatus.COMPLETED else (10 if mapped is GenerationStatus.QUEUED else 50),
            result_url=result,
            error=str(data.get("error") or "") or None,
            raw={"model": model, "status": status},
        )

    def _map_aspect(self, aspect_ratio: str) -> str:
        return {"9:16": "9:16", "16:9": "16:9", "1:1": "1:1"}.get(aspect_ratio, "9:16")

    def _assert_result_url(self, url: str) -> None:
        host = (urlparse(url).hostname or "").lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in _ALLOWED_HOSTS):
            raise RuntimeError("refusing to download a result from an untrusted host")
