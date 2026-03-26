#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT/MissionDispatch"

IMAGE="${MISSION_DATABASE_IMAGE:-nvcr.io/nvidia/isaac/mission-database:4.3.0-amd64}"
CONTAINER_NAME="${MISSION_DATABASE_CONTAINER_NAME:-mission_database}"

existing=$(docker ps -aq --filter "name=^/$CONTAINER_NAME$")
if [ -n "$existing" ]; then
  docker rm -f "$CONTAINER_NAME" || true
fi

docker run -d --name "$CONTAINER_NAME" \
  --network host \
  "$IMAGE" --address 0.0.0.0 --port 5000 --controller_port 5001
