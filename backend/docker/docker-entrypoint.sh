#!/usr/bin/env bash
set -euo pipefail

APP_USER=${APP_USER:-dude}
APP_GROUP=${APP_GROUP:-dudes}
STORAGE_ROOT=${STORAGE_ROOT:-/var/lib/app/storage}

log() {
    printf '[entrypoint] %s\n' "$1"
}

prepare_storage_dir() {
    local target="$1"
    if ! mkdir -p "$target"; then
        log "Failed to create storage directory $target"
        exit 1
    fi
    if ! chown -R "${APP_USER}:${APP_GROUP}" "$target"; then
        log "Failed to chown $target to ${APP_USER}:${APP_GROUP}"
        exit 1
    fi
    if ! chmod 0775 "$target"; then
        log "Failed to chmod $target"
        exit 1
    fi
    log "Storage directory $target prepared for ${APP_USER}:${APP_GROUP}"
}

prepare_storage_dir "$STORAGE_ROOT"

exec gosu "${APP_USER}:${APP_GROUP}" /dude/entrypoints.sh "$@"
