# Architecture

Phase 1 delivered the multi-tenant foundation. Phase 2 added teams, assets, templates, and optional S3/R2 storage. Phase 3 adds workspace credits and billing providers.

MoneyPrinterTurbo is now wrapped by a multi-tenant SaaS foundation. The original video-generation engine is unchanged and remains the source of truth.

## Frontend

- Next.js + React + TypeScript + Tailwind CSS + shadcn-style UI
- Location: `apps/web`
- Routes: `/login`, `/register`, `/dashboard`, `/projects`, `/projects/[id]`, `/create`, `/videos/[id]`, `/templates`, `/settings`
- The browser never waits for a full render. It creates a video/job and polls job status.

## Backend

- New FastAPI app on port **8000**: `apps/api`
- Versioned routes under `/api/v1/`
- JWT authentication, password hashing, workspace authorization in the service layer
- The legacy FastAPI app on port **8080** (`main.py` / `app.asgi:app`) is untouched

## Database

PostgreSQL via SQLAlchemy 2.x + Alembic.

Tables:

- `users`
- `workspaces`
- `workspace_members` (`owner`, `admin`, `editor`, `viewer`)
- `projects` (`workspace_id`)
- `videos` (`workspace_id`)
- `jobs` (`workspace_id`)
- `workspace_invites`
- `assets`
- `templates` (system + workspace)
- `plans`, `credit_packs`, `credit_wallets`, `credit_ledger`, `subscriptions`, `billing_events`

Every workspace-owned row includes `workspace_id`. Access checks happen in `apps/api/services/*`, not only in the UI.

SQLite is supported for local development through `DATABASE_URL=sqlite:///./saas.db`.

## Redis

`REDIS_URL` configures the queue implementation. The API and worker depend on `shared.queue.JobQueue`, not Redis directly.

- Redis: production / Docker
- `memory://`: tests and local runs without Redis

## Worker

`apps/worker/main.py` dequeues jobs and runs `JobRunner`.

```
API → create video + job → enqueue
  → worker → MoneyPrinterTurboGenerationAdapter
  → existing app.services.task functions
  → upload via LocalStorageProvider
  → job COMPLETED / FAILED / CANCELLED
```

Progress is stage-based:

| Stage | Progress |
| --- | --- |
| QUEUED | 0% |
| ANALYZING | 10% |
| GENERATING_SCRIPT | 20% |
| PLANNING | 28% |
| FETCHING_MEDIA | 35% |
| GENERATING_AUDIO | 50% |
| GENERATING_SUBTITLES | 65% |
| RENDERING | 80% |
| UPLOADING | 95% |
| COMPLETED | 100% |

## Generation adapter

`packages/video-engine/video_engine/generation_adapter.py`

Public methods:

- `create_video()`
- `generate_script()`
- `generate_voice()`
- `generate_subtitles()`
- `render_video()`

Internally these call `app.services.task.generate_script`, `generate_audio`, `generate_subtitle`, `get_video_materials`, and `generate_final_videos`. There is no second engine.

## Storage

`packages/shared/shared/storage`

- Interface: `upload_file`, `download_file`, `delete_file`, `get_public_url`, `get_signed_url`
- Implemented: `LocalStorageProvider`
- Prepared: `S3StorageProvider`, `R2StorageProvider` (not implemented in Phase 1)

Existing MoneyPrinterTurbo local task storage (`storage/tasks/...`) is not removed.

Phase 2 storage:

- `LocalStorageProvider` remains the default
- `S3StorageProvider` for AWS S3 or MinIO
- `R2StorageProvider` for Cloudflare R2

Set `STORAGE_PROVIDER=s3` or `r2` plus the `S3_*` environment variables. Local mode still requires no cloud account.

## Phase 2 product layer

- Team invites, roles, and member removal (`/settings`)
- Workspace asset library (`/library`) with upload validation
- System + workspace templates (`/templates`)
- Script preview (`POST /api/v1/scripts/preview`) via the existing LLM adapter
- Local media generation uses workspace assets, downloaded by the worker, then passed to the original `video_source=local` path

## Legacy Streamlit UI

Still available:

```
streamlit run ./webui/Main.py
```

or the original `docker-compose.yml` service on port 8501.

The Next.js app is the new SaaS UI. Streamlit is the safety/legacy UI.

## Phase 3 billing

Credits live on the workspace, not the user.

- New workspaces receive 100 welcome credits on the Free plan
- Creating a video reserves credits (`duration` / 15 × 10, 1080p × 1.25)
- Success captures the reservation
- Failure or cancel refunds it
- `BILLING_PROVIDER=local` completes pack/plan purchases immediately
- `stripe` and `razorpay` adapters exist; they are unused unless keys are set
- Webhooks are idempotent via `billing_events.event_id`

## What was intentionally left untouched

- `app/services/task.py`, `video.py`, `llm.py`, `subtitle.py`, `voice.py`, `material.py`
- MoviePy, FFmpeg, Whisper, Edge/Azure TTS, stock providers
- Legacy `/api/v1` video/llm routes on the original app
- CLI (`cli.py`)
- `config.toml` / `config.example.toml`
- Streamlit WebUI
