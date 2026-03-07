#!/usr/bin/env sh
# Run pytest inside the API Docker container.
# Starts db + redis if needed; runs migrations then pytest.
# Usage: ./scripts/test-in-docker.sh [pytest args...]
# Examples:
#   ./scripts/test-in-docker.sh              # all tests
#   ./scripts/test-in-docker.sh tests/test_import_api.py -v   # Phase 2 import only
set -e
cd "$(dirname "$0")/.."

echo "Running tests in Docker (api container)..."
docker compose run --rm api pytest tests/ -v "$@"
