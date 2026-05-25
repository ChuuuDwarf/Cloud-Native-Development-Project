"""Compatibility exports for the project's async database session."""

from app.core.database import AsyncSessionLocal, engine, get_db

__all__ = ["AsyncSessionLocal", "engine", "get_db"]
