# What to do next

## 1. Local generation (required first)

Local end-to-end is working on this machine. A finished MP4 still needs:

- FFmpeg (or `imageio-ffmpeg`)
- `moviepy` + `edge-tts` in the **same Python** as the worker
- Worker and API sharing jobs (Redis, or the worker claiming `QUEUED` rows from the database)

Without Pexels/OpenAI keys, ShortGen falls back to:

- local script writer
- topic-derived stock terms
- Edge TTS
- bundled stills as clips

```powershell
pip install moviepy==2.2.1 edge-tts==7.2.7 imageio-ffmpeg pillow
python -m apps.worker.main
```

Then generate from http://127.0.0.1:3001/create

## 2. Deploy

- Web: Vercel project on `apps/web`
- API + worker + Postgres + Redis: `docker compose -f docker-compose.saas.yml up --build`

See [DEPLOY.md](DEPLOY.md).

## 3. Live Stripe

Set `ENVIRONMENT=production` only after:

```
BILLING_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
JWT_SECRET=<32+ random chars>
CORS_ORIGINS=https://your-domain
```

Webhook URL: `https://api.your-domain.com/api/v1/billing/webhooks/stripe`

Credits are added only from verified webhooks, never from a success redirect.
`GET /api/v1/billing/status` reports whether Stripe is live-ready.

## 4. Later product

Initiated:

- AI Director (`/director` + `POST /api/v1/director/plan`)
- extra video providers (`GET /api/v1/director/providers`)
- social publish (`POST /api/v1/videos/{id}/publish` wraps `app/services/upload_post.py`)

Runway, Kling, and Luma stay listed as planned. Do not add a second renderer.
