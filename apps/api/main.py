"""SaaS FastAPI application.

This is a new process on port 8000. The legacy MoneyPrinterTurbo API on
port 8080 is unchanged.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from apps.api.bootstrap import REPO_ROOT, ensure_sys_path

ensure_sys_path()

from apps.api.api.deps import get_queue, get_storage
from apps.api.api.routes import api_router
from apps.api.config import get_settings
from apps.api.database.session import get_engine, init_db
from apps.api.services.errors import ServiceError
from shared.security.filenames import safe_object_key
from shared.security import create_rate_limiter

settings = get_settings()
logger = logging.getLogger("saas.api")
rate_limiter = create_rate_limiter(
    settings.rate_limit_backend,
    settings.rate_limit_per_minute,
    settings.redis_url,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        init_db()
    from apps.api.database.session import SessionLocal
    from apps.api.services.billing_catalog import seed_billing_catalog
    from apps.api.services.template_service import seed_system_templates

    db = SessionLocal()
    try:
        seed_billing_catalog(db)
        seed_system_templates(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ShortGen API",
    version="0.1.0",
    description="ShortGen multi-tenant AI video SaaS API.",
    lifespan=lifespan,
)

app.state.queue = get_queue()
app.state.storage = get_storage()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/health") or request.url.path.startswith("/ready"):
        return await call_next(request)
    client = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client):
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    return await call_next(request)


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "invalid request"})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("unhandled API error")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/storage/{object_key:path}")
def read_stored_file(object_key: str):
    try:
        key = safe_object_key(object_key)
        path = Path(settings.storage_path) / key
        resolved = path.resolve()
        if not str(resolved).startswith(str(Path(settings.storage_path).resolve())):
            raise HTTPException(status_code=403, detail="invalid file path")
        if not resolved.is_file():
            raise HTTPException(status_code=404, detail="file not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid file path") from exc
    return FileResponse(resolved)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        app_dir=str(REPO_ROOT),
    )


if __name__ == "__main__":
    run()
