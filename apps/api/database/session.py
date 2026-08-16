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


def init_db() -> None:
    from apps.api import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


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
