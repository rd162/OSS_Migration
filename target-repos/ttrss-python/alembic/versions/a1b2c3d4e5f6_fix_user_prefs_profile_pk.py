"""fix_user_prefs_profile_pk

Fix ttrss_user_prefs primary key: remove profile from PK so profile=NULL is allowed.

The baseline migration created PrimaryKeyConstraint('owner_uid', 'pref_name', 'profile'),
which makes profile NOT NULL in Postgres — preventing inserts for the default profile (NULL).
This migration drops the composite 3-column PK and recreates it as (owner_uid, pref_name) only.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_prefs, lines 364-367)
  PHP schema has NO declared PK; profile IS nullable (NULL = default profile).
  set_pref() uses upsert with profile=None for the default profile — was broken by the PK.

Revision ID: a1b2c3d4e5f6
Revises: 35c0c917fdec
Create Date: 2026-04-05
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "35c0c917fdec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the incorrect 3-column PK that includes the nullable profile column.
    op.drop_constraint("ttrss_user_prefs_pkey", "ttrss_user_prefs", type_="primary")
    # Recreate PK as (owner_uid, pref_name) only — profile stays nullable.
    op.create_primary_key("ttrss_user_prefs_pkey", "ttrss_user_prefs", ["owner_uid", "pref_name"])


def downgrade() -> None:
    # Reverse: drop the 2-column PK and restore the original (broken) 3-column PK.
    # Note: downgrade will fail if any rows have profile=NULL (NOT NULL violation).
    op.drop_constraint("ttrss_user_prefs_pkey", "ttrss_user_prefs", type_="primary")
    op.create_primary_key(
        "ttrss_user_prefs_pkey", "ttrss_user_prefs", ["owner_uid", "pref_name", "profile"]
    )
