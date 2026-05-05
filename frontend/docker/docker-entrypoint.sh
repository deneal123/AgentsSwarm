#!/bin/sh
set -eu

LOCKFILE="/app/package-lock.json"
STAMP_FILE="/app/node_modules/.package-lock.json"

needs_install=0

if [ ! -d /app/node_modules ]; then
  needs_install=1
elif [ ! -f "$STAMP_FILE" ]; then
  needs_install=1
elif ! cmp -s "$LOCKFILE" "$STAMP_FILE"; then
  needs_install=1
fi

if [ "$needs_install" -eq 1 ]; then
  echo "[frontend] Installing npm dependencies..."
  npm install --loglevel error
  mkdir -p /app/node_modules
  cp "$LOCKFILE" "$STAMP_FILE"
else
  echo "[frontend] Using cached node_modules"
fi

exec "$@"
