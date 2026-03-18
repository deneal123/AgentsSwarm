#!/usr/bin/env bash

set -euo pipefail

MODE=${1:-headless}          # headless|gui|check
IMAGE=${IMAGE:-nvcr.io/nvidia/isaac-sim:5.1.0}
ROOT=${ISAAC_ROOT:-$HOME/docker/isaac-sim}
USER_ID=$(id -u)
GROUP_ID=$(id -g)

ESC=$(printf '\033')
GREEN="$ESC[32m"; YELLOW="$ESC[33m"; RED="$ESC[31m"; RESET="$ESC[0m"
info(){ printf "%b%s%b\n" "$GREEN" "$1" "$RESET"; }
warn(){ printf "%b%s%b\n" "$YELLOW" "$1" "$RESET"; }
err(){ printf "%b%s%b\n" "$RED" "$1" "$RESET"; }

usage(){
  cat <<EOF
Usage: $0 [headless|gui|check]

Env vars:
  IMAGE       Docker image tag (default: $IMAGE)
  ISAAC_ROOT  Host directory for caches/configs (default: $ROOT)

Modes:
  headless    run ./runheadless.sh -v
  gui         run ./runapp.sh with X11 forwarding (DISPLAY must be set)
  check       run compatibility check and exit
EOF
}

case "$MODE" in
  headless|gui|check) ;;
  -h|--help) usage; exit 0 ;;
  *) err "Unknown mode: $MODE"; usage; exit 1 ;;
esac

# Prepare host mounts
mkdir -p "$ROOT/cache/main/ov" "$ROOT/cache/main/warp" \
         "$ROOT/cache/computecache" "$ROOT/config" \
         "$ROOT/data/documents" "$ROOT/data/Kit" \
         "$ROOT/logs" "$ROOT/pkg"

# Align permissions to current user for writable mounts
if command -v chown >/dev/null 2>&1; then
  chown -R "$USER_ID:$GROUP_ID" "$ROOT" || true
fi

COMMON_MOUNTS=(
  -v "$ROOT/cache/main:/isaac-sim/.cache:rw"
  -v "$ROOT/cache/computecache:/isaac-sim/.nv/ComputeCache:rw"
  -v "$ROOT/logs:/isaac-sim/.nvidia-omniverse/logs:rw"
  -v "$ROOT/config:/isaac-sim/.nvidia-omniverse/config:rw"
  -v "$ROOT/data:/isaac-sim/.local/share/ov/data:rw"
  -v "$ROOT/pkg:/isaac-sim/.local/share/ov/pkg:rw"
)

COMMON_ENV=(
  -e ACCEPT_EULA=Y
  -e PRIVACY_CONSENT=Y
)

COMMON_ARGS=(
  --name isaac-sim
  --rm
  --gpus all
  --network=host
  -u "$USER_ID:$GROUP_ID"
  "${COMMON_ENV[@]}"
  "${COMMON_MOUNTS[@]}"
)

if ! command -v docker >/dev/null 2>&1; then
  err "Docker не найден. Установите Docker и NVIDIA Container Toolkit."
  exit 1
fi

case "$MODE" in
  headless)
    info "Запуск Isaac Sim в headless режиме"
    exec docker run "${COMMON_ARGS[@]}" "$IMAGE" ./runheadless.sh -v
    ;;
  gui)
    : "${DISPLAY:=:0}"
    info "Запуск Isaac Sim с GUI (DISPLAY=$DISPLAY)"
    if command -v xhost >/dev/null 2>&1; then
      xhost +local:root >/dev/null 2>&1 || true
    else
      warn "xhost не найден, убедитесь что X11 сервер разрешает соединения."
    fi
    GUI_ARGS=(
      -e DISPLAY
      -v "$HOME/.Xauthority:/isaac-sim/.Xauthority:ro"
    )
    exec docker run "${COMMON_ARGS[@]}" "${GUI_ARGS[@]}" "$IMAGE" ./runapp.sh
    ;;
  check)
    info "Запуск совместимость-проверки"
    exec docker run "${COMMON_ARGS[@]}" "$IMAGE" ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
    ;;
esac