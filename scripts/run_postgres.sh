#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT/MissionDispatch"

if [ -z "$POSTGRES_PASSWORD" ]; then
  echo "POSTGRES_PASSWORD is not set. Using default 'postgres'."
  POSTGRES_PASSWORD="postgres"
fi

docker run --rm --name postgres \
  --network host \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB=mission \
  -d postgres:14.5

