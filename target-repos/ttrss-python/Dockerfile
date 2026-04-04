# New: no PHP equivalent — multi-stage Docker image for Python migration.
# Phase 6 B3: production hardening (R05, R06, AR02, AR10).

# ---------------------------------------------------------------------------
# Stage 1: builder — gcc + libpq-dev for psycopg2 compile only
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/runtime-deps .

# ---------------------------------------------------------------------------
# Stage 2: runtime — libpq5 only, no build tools (AR10: minimal attack surface)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /runtime-deps /usr/local
COPY ttrss/ ./ttrss/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY gunicorn.conf.py .
COPY scripts/ ./scripts/

# R06/AR02: NO ARG/ENV for secrets — inject at runtime via env_file or -e flags.
# Never bake DATABASE_URL, SECRET_KEY, FEED_CRYPT_KEY into the image.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# R05: Default CMD is the web process; override command for worker/beat roles.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "ttrss:create_app()"]
