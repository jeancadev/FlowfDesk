"""
SQLAlchemy Database Session Management.

Provides the engine, session factory, and base class for ORM models.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


def get_engine():
    """Create SQLAlchemy engine from settings."""
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.FLASK_DEBUG,
    )


def get_session_factory():
    """Create a session factory bound to the engine."""
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    """Get a new database session."""
    factory = get_session_factory()
    return factory()
