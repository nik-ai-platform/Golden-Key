#!/usr/bin/env bash
set -euo pipefail

echo "================================="
echo " Golden Key Production Deployment"
echo "================================="

PROJECT_DIR="/opt/golden-key"
COMPOSE=(docker compose --env-file .env.production -f docker-compose.production.yml)

cd "$PROJECT_DIR"

echo
echo "[1/7] Pulling latest source..."
git pull --ff-only

echo
echo "[2/7] Validating Compose..."
"${COMPOSE[@]}" config --quiet

echo
echo "[3/7] Building images..."
"${COMPOSE[@]}" build

echo
echo "[4/7] Starting database..."
"${COMPOSE[@]}" up -d db

echo
echo "[5/7] Starting application..."
"${COMPOSE[@]}" up -d

echo
echo "[6/7] Waiting for backend health..."
for attempt in {1..30}; do
    if "${COMPOSE[@]}" exec -T backend curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
        break
    fi
    if [[ "$attempt" -eq 30 ]]; then
        echo "Backend did not become healthy in time." >&2
        "${COMPOSE[@]}" logs backend --tail=100
        exit 1
    fi
    sleep 2
done
"${COMPOSE[@]}" ps

echo
echo "[7/7] Checking backend..."
"${COMPOSE[@]}" exec -T backend python -c \
    "from app.main import app; print('Golden Key backend loaded')"

echo
echo "================================="
echo " Deployment complete"
echo "================================="