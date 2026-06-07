#!/bin/sh
set -e

# The /app/node_modules volume can outlive image rebuilds; reinstall when deps change.
STAMP="/app/node_modules/.docker-install-stamp"
LOCK_HASH="$(md5sum package-lock.json 2>/dev/null | cut -d' ' -f1 || md5 -q package-lock.json)"

needs_install() {
  if [ ! -x node_modules/.bin/next ]; then
    return 0
  fi
  if [ ! -f "$STAMP" ]; then
    return 0
  fi
  if [ "$(cat "$STAMP" 2>/dev/null)" != "$LOCK_HASH" ]; then
    return 0
  fi
  return 1
}

if needs_install; then
  echo "Installing frontend dependencies..."
  npm ci
  echo "$LOCK_HASH" > "$STAMP"
fi

exec ./node_modules/.bin/next dev --hostname 0.0.0.0 --port 3000
