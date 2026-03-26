#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT/MissionDispatch"

IMAGE="${MISSION_DISPATCH_IMAGE:-nvcr.io/nvidia/isaac/mission-dispatch:4.3.0-amd64}"
CONTAINER_NAME="${MISSION_DISPATCH_CONTAINER_NAME:-mission_dispatch}"

existing=$(docker ps -aq --filter "name=^/$CONTAINER_NAME$")
if [ -n "$existing" ]; then
  docker rm -f "$CONTAINER_NAME" || true
fi

docker run -d --name "$CONTAINER_NAME" \
  --network host \
  "$IMAGE"