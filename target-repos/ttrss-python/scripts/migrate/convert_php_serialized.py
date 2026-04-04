#!/usr/bin/env python3
"""Post-pgloader: PHP serialize() blobs → JSON in ttrss_plugin_storage.

New: no PHP equivalent — PHP serialize() is not present in PHP source.
Requires phpserialize (added to pyproject.toml in Phase 6 B5).
AR07: exits non-zero if ANY rows fail to deserialize.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate/convert_php_serialized.py
"""
import json
import logging
import os
import sys

import phpserialize
import sqlalchemy as sa

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    log.error("DATABASE_URL environment variable is required")
    sys.exit(2)

engine = sa.create_engine(database_url)
failed = 0
converted = 0

with engine.begin() as conn:
    rows = conn.execute(sa.text(
        "SELECT id, content FROM ttrss_plugin_storage "
        "WHERE content LIKE 'a:%' OR content LIKE 's:%' OR content LIKE 'i:%'"
    )).fetchall()

    log.info("Found %d PHP-serialized rows to convert", len(rows))

    for row_id, content in rows:
        try:
            raw = content.encode() if isinstance(content, str) else content
            deserialized = phpserialize.loads(raw)
            json_content = json.dumps(deserialized, default=str)
            conn.execute(
                sa.text("UPDATE ttrss_plugin_storage SET content = :v WHERE id = :id"),
                {"v": json_content, "id": row_id},
            )
            converted += 1
        except Exception as exc:
            log.error("Row id=%s failed: %s (preview: %.80r)", row_id, exc, content)
            failed += 1

log.info("Converted: %d  Failed: %d", converted, failed)

if failed > 0:
    log.error("FAIL: %d unconverted rows — inspect above before proceeding", failed)
    sys.exit(1)

sys.exit(0)
