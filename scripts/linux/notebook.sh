#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}:$PYTHONPATH"

# Add poetry to PATH if installed in standard locations
if [ -d "$HOME/.local/bin" ]; then
	export PATH="$HOME/.local/bin:$PATH"
fi
if [ -d "$HOME/.poetry/bin" ]; then
	export PATH="$HOME/.poetry/bin:$PATH"
fi

cd "$PROJECT_ROOT"

MODE=""

ESC="$(printf '\033')"
RED="$ESC[31m"
GREEN="$ESC[32m"
YELLOW="$ESC[33m"
BLUE="$ESC[34m"
RESET="$ESC[0m"

echoinfo() {
	printf "%b%s%b\n" "$GREEN" "$1" "$RESET"
}
echowarn() {
	printf "%b%s%b\n" "$YELLOW" "$1" "$RESET"
}
echoerr() {
	printf "%b%s%b\n" "$RED" "$1" "$RESET"
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

start_jupyter() {
	if [ "$MODE" = "poetry" ]; then
		# try notebook module
		if poetry run python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('notebook') else 1)
PY
		then
			poetry run python -m notebook --notebook-dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		# try jupyter_server if notebook not present
		if poetry run python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('jupyter_server') else 1)
PY
		then
			poetry run python -m jupyter_server --ServerApp.root_dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		echowarn "jupyter_server/notebook not found in poetry environment. Install with: poetry add --group dev notebook"
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
		# try notebook module first
		if python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('notebook') else 1)
PY
		then
			python -m notebook --notebook-dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		# try jupyter_server if notebook not present
		if python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('jupyter_server') else 1)
PY
		then
			python -m jupyter_server --ServerApp.root_dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		echoerr "jupyter_server/notebook not found in active venv. Install: pip install notebook"
	else
		# try notebook module first
		if python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('notebook') else 1)
PY
		then
			python -m notebook --notebook-dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		if python - <<'PY'
import pkgutil,sys
sys.exit(0 if pkgutil.find_loader('jupyter_server') else 1)
PY
		then
			python -m jupyter_server --ServerApp.root_dir="$PROJECT_ROOT/src" --allow-root
			return
		fi
		echoerr "jupyter_server/notebook not found. Install: pip install notebook"
	fi
}

detect_mode
echoinfo "RUN_MODE=$MODE (source: ${RUNMODE_SOURCE:-unknown})"
start_jupyter
