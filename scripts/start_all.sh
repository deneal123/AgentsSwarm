#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT/MissionDispatch"

# Cleanup previous if exists in any state
for c in mission_dispatch mission_database postgres mosquitto; do
  cid=$(docker ps -aq --filter "name=^/$c$")
  if [ -n "$cid" ]; then
    docker rm -f "$c" || true
  fi
done

bash ../scripts/run_postgres.sh
bash ../scripts/run_mqtt_broker.sh
bash ../scripts/run_mission_database.sh
bash ../scripts/run_mission_dispatch.sh