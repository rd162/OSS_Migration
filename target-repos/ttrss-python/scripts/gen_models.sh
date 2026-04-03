#!/usr/bin/env bash
# gen_models.sh — Generate sqlacodegen reference output for schema verification.
#
# This script is a DEVELOPMENT TOOL ONLY.
# AR08: sqlacodegen is NOT in pyproject.toml — install manually: pip install sqlacodegen
# AR03: output goes to scripts/sqlacodegen_reference/ — NEVER to ttrss/models/
#
# Workflow:
#   1. docker compose up db        (start Postgres)
#   2. alembic upgrade head        (apply migrations)
#   3. ./scripts/gen_models.sh     (generate reference scaffold)
#   4. diff scripts/sqlacodegen_reference/models_ref.py against ttrss/models/
#   5. Update model files if schema has drifted
#
# Usage:
#   DATABASE_URL=postgresql://ttrss:ttrss@localhost:5432/ttrss ./scripts/gen_models.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/sqlacodegen_reference"
mkdir -p "${OUTPUT_DIR}"

: "${DATABASE_URL:?DATABASE_URL must be set (e.g. postgresql://ttrss:ttrss@localhost/ttrss)}"

echo "Running sqlacodegen against: ${DATABASE_URL}"
echo "Output: ${OUTPUT_DIR}/models_ref.py"
echo ""

sqlacodegen \
  --generator declarative \
  "${DATABASE_URL}" \
  > "${OUTPUT_DIR}/models_ref.py"

echo "Done."
echo ""
echo "NEXT STEPS:"
echo "  Compare ${OUTPUT_DIR}/models_ref.py against ttrss/models/"
echo "  Update any model files that have drifted from the live schema."
echo ""
echo "WARNING: Do NOT import from sqlacodegen_reference/ in production code (AR03)."
