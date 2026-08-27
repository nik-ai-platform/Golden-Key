#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="${1:-/backups}"
LATEST_DB="$(find "$BACKUP_ROOT" -maxdepth 1 -name 'database-*.sql' | sort | tail -n 1 || true)"

if [ -n "$LATEST_DB" ]; then
  echo "Restoring database from $LATEST_DB"
  psql "${DATABASE_URL}" < "$LATEST_DB"
else
  echo "No database backup found"
fi
