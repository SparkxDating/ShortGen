# Development

Phase 1 is the SaaS foundation. Phase 2 adds team invites, the asset library, templates, and optional S3/R2 storage. Phase 3 adds workspace credits and local/Stripe/Razorpay billing.

## Install dependencies

From the repository root.

Existing engine (unchanged):

```powershell
uv sync
```

or

```powershell
pip install -r requirements.txt
```

SaaS extras:

```powershell
uv sync --extra saas
```

or

```powershell
pip install -r requirements-saas.txt
```

Frontend:

```powershell
cd apps/web
npm install
```

Copy environment:

```powershell
copy .env.example .env
```

Set `JWT_SECRET` to a long random string before any shared deployment.

## Start PostgreSQL

Docker:

```powershell
docker compose -f docker-compose.saas.yml up postgres -d
```

Local URL:

```
DATABASE_URL=postgresql+psycopg://mpt:mpt@localhost:5432/moneyprinterturbo
```

Without Postgres, use SQLite:

```
DATABASE_URL=sqlite:///./saas.db
```

## Start Redis

```powershell
docker compose -f docker-compose.saas.yml up redis -d
```

Without Redis:

```
REDIS_URL=memory://
```

The API will also fall back to the in-memory queue if Redis is unreachable.

## Run migrations

`init_db()` creates tables on API/worker startup. To use Alembic explicitly:

```powershell
alembic -c infrastructure/migrations/alembic.ini upgrade head
```

## Start the SaaS API

```powershell
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Health: http://127.0.0.1:8000/health
Docs: http://127.0.0.1:8000/docs

## Start the worker

```powershell
python -m apps.worker.main
```

## Start Next.js

```powershell
cd apps/web
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
npm run dev
```

Open http://127.0.0.1:3000

## Full SaaS stack

```powershell
docker compose -f docker-compose.saas.yml up --build
```

## Legacy MoneyPrinterTurbo

These commands are unchanged:

```powershell
python main.py
streamlit run ./webui/Main.py
docker compose up
```

Legacy API: http://127.0.0.1:8080
Legacy WebUI: http://127.0.0.1:8501

## Tests

SaaS tests (mocked generation, no paid providers):

```powershell
pytest test/saas -q
```

Existing engine tests:

```powershell
pytest test/services -q
```

## Local generation notes

- The SaaS worker calls the **existing** MoneyPrinterTurbo pipeline.
- LLM/TTS/stock keys still come from `config.toml` plus `OPENAI_API_KEY` / `GEMINI_API_KEY` in `.env` if you set them there for later phases.
- Do not expect a completed video without the same keys and FFmpeg the legacy app already needs.
