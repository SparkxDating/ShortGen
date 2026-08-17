# Deploy ShortGen

## Web (Vercel)

From `apps/web`:

```powershell
npx vercel --yes
```

Environment:

```
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

The Next.js app cannot run MoviePy. Keep generation on the API/worker.

## API + worker

```powershell
docker compose -f docker-compose.saas.yml up --build -d
```

Services: Postgres, Redis, API `:8000`, worker, web `:3000`.

Postgres and Redis stay on the compose network only, so they do not steal host ports `5432` / `6379`. To publish the API/web on other host ports, add a local compose override.

Production:

```
ENVIRONMENT=production
AUTO_CREATE_SCHEMA=false
BILLING_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
JWT_SECRET=...
CORS_ORIGINS=https://shortgen.example
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg://mpt:mpt@postgres:5432/moneyprinterturbo
```

Then:

```powershell
alembic -c infrastructure/migrations/alembic.ini upgrade head
```

Stripe webhook: `https://api.your-domain.com/api/v1/billing/webhooks/stripe`

Do not set `BILLING_PROVIDER=local` in production. The API refuses to start.
