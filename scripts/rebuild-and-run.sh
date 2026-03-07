#!/usr/bin/env sh
# Stop, rebuild, and run the stack. Usage: ./scripts/rebuild-and-run.sh [--no-cache]
set -e
cd "$(dirname "$0")/.."

echo "Stopping containers..."
docker compose down

echo "Rebuilding images..."
if [ "$1" = "--no-cache" ]; then
  docker compose build --no-cache
else
  docker compose build
fi

echo "Starting services..."
docker compose up
