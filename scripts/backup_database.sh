#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/golden-key"
BACKUP_DIR="$PROJECT_DIR/backups"
COMPOSE=(docker compose --env-file .env.production -f docker-compose.production.yml)

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="$BACKUP_DIR/goldenkey-$TIMESTAMP.sql"

cd "$PROJECT_DIR"

POSTGRES_DB=$(grep -m1 '^POSTGRES_DB=' .env.production | cut -d= -f2-)
POSTGRES_USER=$(grep -m1 '^POSTGRES_USER=' .env.production | cut -d= -f2-)

"${COMPOSE[@]}" exec -T db \
    pg_dump \
    -U "$POSTGRES_USER" \
    "$POSTGRES_DB" \
    > "$BACKUP_FILE"

gzip "$BACKUP_FILE"

echo "Backup created:"
echo "${BACKUP_FILE}.gz"