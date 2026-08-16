# ShortGen

ShortGen is a multi-tenant AI video SaaS for creating short-form videos from a topic.

The product UI is Next.js. Generation still uses the existing MoneyPrinterTurbo engine — it is wrapped, not rewritten.

## Product

- Register, login, workspaces, and roles
- Projects, video jobs, and live generation progress
- Team invites and an asset library
- Templates
- Workspace credits and local billing (Stripe/Razorpay adapters optional)

## Local development

```powershell
cd C:\Users\manoj\MoneyPrinterTurbo
copy .env.example .env

# API
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Worker
python -m apps.worker.main

# Web
cd apps\web
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
npm install
npm run dev
```

Open http://127.0.0.1:3000 (or 3001 if 3000 is already in use).

SQLite and `REDIS_URL=memory://` work without Docker. PostgreSQL and Redis are available in `docker-compose.saas.yml`.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Development](docs/DEVELOPMENT.md)

## Legacy engine UI

The original Streamlit WebUI is still available:

```powershell
streamlit run .\webui\Main.py
```
