#!/usr/bin/env bash
# New: no PHP equivalent — pre-migration audit script.
# Phase 6 B5: R12 (timezone), R13/AR09 (zero dates), R16 (4-byte emoji).
#
# Usage:
#   MYSQL_HOST=... MYSQL_USER=... MYSQL_PASS=... MYSQL_DB=... \
#     ./scripts/migrate/pre_migration_audit.sh [--allow-emoji]
#
# Exits 0 only if all checks pass (or operator passes --allow-emoji for emoji rows).

set -euo pipefail

ALLOW_EMOJI=false
for arg in "$@"; do
    [[ "$arg" == "--allow-emoji" ]] && ALLOW_EMOJI=true
done

: "${MYSQL_HOST:?MYSQL_HOST is required}"
: "${MYSQL_USER:?MYSQL_USER is required}"
: "${MYSQL_PASS:?MYSQL_PASS is required}"
: "${MYSQL_DB:?MYSQL_DB is required}"

MYSQL_CMD="mysql -h ${MYSQL_HOST} -u ${MYSQL_USER} -p${MYSQL_PASS} ${MYSQL_DB}"

echo "=== R12: Timezone audit ==="
${MYSQL_CMD} -e "SELECT @@global.time_zone, @@session.time_zone;"

echo ""
echo "=== R13/AR09: Zero-date prevalence (including date-only columns) ==="
${MYSQL_CMD} -e "
  SELECT 'ttrss_entries.updated', COUNT(*)
    FROM ttrss_entries WHERE updated='0000-00-00 00:00:00'
  UNION ALL
  SELECT 'ttrss_entries.date_entered', COUNT(*)
    FROM ttrss_entries WHERE date_entered='0000-00-00';
"

echo ""
echo "=== R16: 4-byte emoji check ==="
EMOJI_COUNT=$(${MYSQL_CMD} --skip-column-names -e \
  "SELECT COUNT(*) FROM ttrss_entries \
   WHERE content REGEXP '[\\\\xF0-\\\\xF7][\\\\x80-\\\\xBF]{3}';")
echo "Rows with 4-byte emoji: ${EMOJI_COUNT}"
if [[ "${EMOJI_COUNT}" -gt 0 && "${ALLOW_EMOJI}" == "false" ]]; then
    echo "ERROR: ${EMOJI_COUNT} rows have 4-byte emoji."
    echo "Verify utf8mb4 handling in pgloader.load, then re-run with --allow-emoji."
    exit 1
fi

echo ""
echo "=== Audit complete — all gates passed ==="
