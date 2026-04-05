"""add_pg_trgm_extension

Install pg_trgm extension required by _is_ngram_duplicate() in persist.py.

Source: ttrss/articles/persist.py:_is_ngram_duplicate — uses PostgreSQL
  similarity() function from pg_trgm to detect near-duplicate article titles.
  Without this extension, the first call to similarity() aborts the transaction,
  preventing all subsequent articles from being persisted (InFailedSqlTransaction).

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05
"""
from __future__ import annotations

from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
