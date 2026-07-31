"""Shared SQLAlchemy metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for Launch Kit persistence records."""
