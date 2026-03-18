#!/bin/bash

set -e
SCRIPT_PATH="$1"
shift
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PROJECT_PATH="$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_PATH:$PYTHONPATH"

# Add poetry to PATH if installed in standard locations
if [ -d "$HOME/.local/bin" ]; then
	export PATH="$HOME/.local/bin:$PATH"
fi
if [ -d "$HOME/.poetry/bin" ]; then
	export PATH="$HOME/.poetry/bin:$PATH"
fi

ESC="$(printf '\033')"
RED="$ESC[31m"
GREEN="$ESC[32m"
YELLOW="$ESC[33m"
BLUE="$ESC[34m"
RESET="$ESC[0m"

echoinfo() {
  printf "%b%s%b\n" "$GREEN" "$1" "$RESET"
}

detect_mode() {
  if [ -n "$RUN_MODE" ]; then
    MODE="$RUN_MODE"
    RUNMODE_SOURCE=environment
    return
  fi
  if [ -f "$PROJECT_ROOT/.env" ]; then
    _val=$(grep -E '^RUN_MODE=' "$PROJECT_ROOT/.env" || true)
    if [ -n "$_val" ]; then
      MODE=${_val#RUN_MODE=}
      RUNMODE_SOURCE=file
      return
    fi
  fi
  if command -v poetry >/dev/null 2>&1; then
    MODE=poetry
    RUNMODE_SOURCE="auto(poetry)"
  elif [ -f "$PROJECT_ROOT/.venv/bin/activate" ] || [ -f "./.venv/bin/activate" ]; then
    MODE=legacy
    RUNMODE_SOURCE="auto(.venv)"
  elif [ -f "$PROJECT_ROOT/venv/bin/activate" ] || [ -f "./venv/bin/activate" ]; then
    MODE=legacy
    RUNMODE_SOURCE="auto(venv)"
  else
    MODE=direct
    RUNMODE_SOURCE="auto(direct)"
  fi
}

detect_mode
echoinfo "RUN_MODE=$MODE (source: ${RUNMODE_SOURCE:-unknown})"

if [ "$MODE" = "poetry" ]; then
    poetry run python "$SCRIPT_PATH" "$@"
elif [ "$MODE" = "legacy" ]; then
    if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
        source "$PROJECT_ROOT/.venv/bin/activate"
    elif [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    elif [ -f "./.venv/bin/activate" ]; then
        source "./.venv/bin/activate"
    elif [ -f "./venv/bin/activate" ]; then
        source "./venv/bin/activate"
    fi
    python "$SCRIPT_PATH" "$@"
else
    python "$SCRIPT_PATH" "$@"
fi
