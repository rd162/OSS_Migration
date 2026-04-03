"""
Alembic migration environment.
target_metadata = Base.metadata ensures autogenerate sees all 31 models (CG-06, R06).
DATABASE_URL is read from environment — not from alembic.ini (R03, AR01).

New: no PHP equivalent — Alembic replaces ttrss/classes/dbupdater.php:DbUpdater
     (PHP ran raw SQL version upgrade files in ttrss/schema/versions/pgsql/*.sql;
     Alembic generates and applies migrations from ORM metadata instead).
Source schema baseline: ttrss/schema/ttrss_schema_pgsql.sql
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so they register with Base.metadata before autogenerate runs
import ttrss.models  # noqa: F401 — side-effect import; registers all 31 mappers (Phase 1b)
from ttrss.models.base import Base

target_metadata = Base.metadata  # single metadata for all 31 active tables


def get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    return config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
