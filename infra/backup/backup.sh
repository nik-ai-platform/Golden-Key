#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/backups}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
mkdir -p "$BACKUP_ROOT"

if [ -n "${DATABASE_URL:-}" ]; then
  echo "Backing up database..."
  pg_dump "${DATABASE_URL}" > "$BACKUP_ROOT/database-$TIMESTAMP.sql"
fi

if [ -n "${STORAGE_BUCKET:-}" ]; then
  echo "Backing up object storage manifest..."
  printf '%s\n' "${STORAGE_BUCKET}" > "$BACKUP_ROOT/storage-$TIMESTAMP.txt"
fi

if [ -d "infra" ]; then
  echo "Backing up configuration..."
  cp -R infra "$BACKUP_ROOT/infra-$TIMESTAMP"
fi

echo "Backup completed: $BACKUP_ROOT"
