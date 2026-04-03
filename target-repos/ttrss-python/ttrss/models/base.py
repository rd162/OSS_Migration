"""
Single authoritative DeclarativeBase for all 10 ORM models (A-NC-02/03).
All model files import Base from here. No other DeclarativeBase exists.
Alembic env.py imports Base.metadata from here for autogenerate (CG-06).
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
