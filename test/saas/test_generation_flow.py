from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from apps.api.database.session import SessionLocal
from apps.worker.runner import JobRunner
from test.saas.conftest import auth_header, register
from video_engine.generation_adapter import GenerationError, GenerationResult


@dataclass
class FakeAdapter:
    fail: bool = False
    stages: list[str] = field(default_factory=list)

    def create_video(
        self,
        payload: dict[str, Any],
        *,
        task_id: str | None = None,
        on_progress: Callable | None = None,
        should_cancel: Callable | None = None,
    ) -> GenerationResult:
        for stage in (
            "ANALYZING",
            "GENERATING_SCRIPT",
            "PLANNING",
            "GENERATING_AUDIO",
            "GENERATING_SUBTITLES",
            "FETCHING_MEDIA",
            "RENDERING",
        ):
            self.stages.append(stage)
            if on_progress:
                on_progress(stage, 10, None)
        if self.fail:
            raise GenerationError("mocked provider failure")
        return GenerationResult(
            task_id=task_id or "saas-test",
            script="A short script about oceans.",
            audio_duration=12,
            video_paths=[],
            raw={"pipeline": "existing-moneyprinterturbo"},
        )


def _create_video(client, email: str):
    user = register(client, email)
    headers = auth_header(user["access_token"])
    workspace = client.get("/api/v1/workspaces", headers=headers).json()[0]
    project = client.post(
        "/api/v1/projects",
        json={"workspace_id": workspace["id"], "name": "Flow", "description": ""},
        headers=headers,
    ).json()
    video = client.post(
        "/api/v1/videos",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "title": "Ocean",
            "topic": "Ocean facts",
        },
        headers=headers,
    ).json()
    return headers, video


def test_api_job_worker_adapter_pipeline(client, tmp_path):
    headers, video = _create_video(client, "flow@example.com")
    job_id = video["latest_job"]["id"]
    adapter = FakeAdapter()
    db = SessionLocal()
    try:
        runner = JobRunner(
            db,
            client.app.state.queue,
            client.app.state.storage,
            adapter_factory=lambda: adapter,
        )
        completed = runner.process_job(job_id)
        assert completed.status == "COMPLETED"
        assert completed.current_stage == "COMPLETED"
        assert "GENERATING_SCRIPT" in adapter.stages
        assert completed.output_data["script"] == "A short script about oceans."
    finally:
        db.close()

    fetched = client.get(f"/api/v1/videos/{video['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"
    assert fetched.json()["progress"] == 100


def test_generation_failure_marks_job_failed(client):
    headers, video = _create_video(client, "fail@example.com")
    job_id = video["latest_job"]["id"]
    db = SessionLocal()
    try:
        runner = JobRunner(
            db,
            client.app.state.queue,
            client.app.state.storage,
            adapter_factory=lambda: FakeAdapter(fail=True),
        )
        failed = runner.process_job(job_id)
        assert failed.status == "FAILED"
        assert "mocked provider failure" in (failed.error_message or "")
    finally:
        db.close()

    job = client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()
    assert job["status"] == "FAILED"
    video_body = client.get(f"/api/v1/videos/{video['id']}", headers=headers).json()
    assert video_body["status"] == "failed"


def test_adapter_calls_existing_task_functions(monkeypatch):
    import sys
    import types

    from video_engine.generation_adapter import MoneyPrinterTurboGenerationAdapter

    calls: list[str] = []

    class Params:
        video_source = "pexels"
        video_subject = "ocean"
        video_language = "en-US"
        voice_name = "en-US-JennyNeural-Female"
        video_clip_duration = 5
        paragraph_number = 1
        subtitle_enabled = True
        video_script = ""

    fake_task = types.ModuleType("app.services.task")

    def generate_terms(task_id, params, script):
        calls.append("generate_terms")
        return ["ocean"]

    def save_script_data(*args, **kwargs):
        calls.append("save_script_data")

    fake_task.generate_terms = generate_terms
    fake_task.save_script_data = save_script_data
    monkeypatch.setitem(sys.modules, "app.services.task", fake_task)

    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "build_params",
        lambda self, payload: Params(),
    )
    monkeypatch.setattr(MoneyPrinterTurboGenerationAdapter, "_ensure_engine", lambda self: None)
    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "generate_script",
        lambda self, task_id, params: calls.append("generate_script") or "script",
    )
    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "generate_voice",
        lambda self, task_id, params, script: (calls.append("generate_audio") or "/tmp/audio.mp3", 8, object()),
    )
    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "generate_subtitles",
        lambda self, *args, **kwargs: calls.append("generate_subtitle") or "/tmp/subtitle.srt",
    )
    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "fetch_media",
        lambda self, *args, **kwargs: calls.append("get_video_materials") or ["/tmp/clip.mp4"],
    )
    monkeypatch.setattr(
        MoneyPrinterTurboGenerationAdapter,
        "render_video",
        lambda self, *args, **kwargs: calls.append("generate_final_videos") or (["/tmp/final.mp4"], [], []),
    )

    adapter = MoneyPrinterTurboGenerationAdapter()
    result = adapter.create_video({"topic": "ocean"})
    assert result.primary_video_path == "/tmp/final.mp4"
    assert calls == [
        "generate_script",
        "generate_terms",
        "save_script_data",
        "generate_audio",
        "generate_subtitle",
        "get_video_materials",
        "generate_final_videos",
    ]
