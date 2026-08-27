#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage:"
    echo "./scripts/rollback.sh <git-tag-or-commit>"
    exit 1
fi

TARGET="$1"
PROJECT_DIR="/opt/golden-key"
COMPOSE=(docker compose --env-file .env.production -f docker-compose.production.yml)

cd "$PROJECT_DIR"

echo "Backing up database..."
./scripts/backup_database.sh

echo "Checking out $TARGET..."
git fetch --all --tags
git checkout --detach "$TARGET"

echo "Rebuilding application..."
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d

echo "Rollback complete. Repository is detached at $TARGET."