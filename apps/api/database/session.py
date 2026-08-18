from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import get_settings
from apps.api.database.base import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
        _engine = create_engine(
            settings.database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            future=True,
            class_=Session,
        )
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def _ensure_sqlite_columns(engine: Engine) -> None:
    """Add columns create_all will not add on an existing local SQLite file."""
    settings = get_settings()
    if not settings.is_sqlite:
        return
    patches = {
        "jobs": (
            ("heartbeat_at", "DATETIME"),
            ("worker_id", "VARCHAR(80)"),
            ("attempt_started_at", "DATETIME"),
        ),
        "videos": (
            ("visual_mode", "VARCHAR(20) DEFAULT 'stock'"),
            ("plan_json", "JSON"),
        ),
    }
    with engine.begin() as connection:
        for table, columns in patches.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            if not existing:
                continue
            for name, ddl in columns:
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    from apps.api import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns(engine)


# Backwards-friendly aliases used by the worker and health checks.
engine = property(lambda self: get_engine())  # type: ignore[assignment]


class _EngineProxy:
    def connect(self):
        return get_engine().connect()

    def dispose(self):
        return get_engine().dispose()


engine = _EngineProxy()  # type: ignore[assignment]


def SessionLocal() -> Session:
    return get_session_factory()()
