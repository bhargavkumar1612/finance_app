#!/usr/bin/env sh
# Run pytest inside the API Docker container.
# Usage: ./scripts/test-in-docker.sh [pytest args...]
set -e
cd "$(dirname "$0")/.."

echo "Running tests in Docker (api container)..."
docker compose run --rm \
  -w /app/apps/api \
  -e PYTHONPATH=/app/apps/api \
  api pytest "$@"
