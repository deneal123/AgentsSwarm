#!/usr/bin/env bash


ensure_database_exists() {
    echo "Checking if database '${POSTGRESQL__DB}' exists..."

    PGPASSWORD="${POSTGRESQL__PASSWORD}" psql -h "${POSTGRESQL__HOST}" -p "${POSTGRESQL__PORT}" -U "${POSTGRESQL__USER}" -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '${POSTGRESQL__DB}'" | grep -q 1

    if [ $? -ne 0 ]; then
        echo "Database '${POSTGRESQL__DB}' does not exist. Creating..."
        PGPASSWORD="${POSTGRESQL__PASSWORD}" psql -h "${POSTGRESQL__HOST}" -p "${POSTGRESQL__PORT}" -U "${POSTGRESQL__USER}" -d postgres -c \
            "CREATE DATABASE ${POSTGRESQL__DB};"
        echo "Database '${POSTGRESQL__DB}' created successfully."
    else
        echo "Database '${POSTGRESQL__DB}' already exists."
    fi
}

case "$1" in

    "server")
        echo "Starting server ..."
        
        ensure_database_exists
        echo "Preparing database for migrations"
        
        PSQL_BASE=( -h "${POSTGRESQL__HOST}" -p "${POSTGRESQL__PORT}" -U "${POSTGRESQL__USER}" -d "${POSTGRESQL__DB}" -c )

        if PGPASSWORD="${POSTGRESQL__PASSWORD}" psql "${PSQL_BASE[@]}" "CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(255) NOT NULL);"; then
            echo "Created alembic_version table if missing (or it already existed)"
        else
            echo "Warning: failed to create alembic_version table (continuing)" >&2
        fi

        if PGPASSWORD="${POSTGRESQL__PASSWORD}" psql "${PSQL_BASE[@]}" "ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE varchar(255);"; then
            echo "Ensured alembic_version.version_num column wide enough"
        else
            echo "Warning: could not alter alembic_version column or it already fits" >&2
        fi

        echo "Running database migrations (alembic upgrade heads)"
        if ! alembic -c /dude/alembic/alembic.ini upgrade heads; then
            echo "Alembic migration failed" >&2
            exit 1
        fi
        
        RELOAD_ARGS=""
        if [ "${MODE}" = "dev" ]; then
            echo "Starting in reload mode"
            RELOAD_ARGS="--reload"
        fi
        
        exec python -m uvicorn service.main:app \
            --host 0.0.0.0 \
            --port ${SERVERS__SERVICE_BACKEND_PORT:-8000} \
            --proxy-headers \
            ${RELOAD_ARGS}
        ;;

    "celery")
        shift
        echo "Starting celery $@"
        exec python -m celery -A service.infrastructure.messaging.celery_app "$@"
        ;;

    *)
        echo "Unknown command: $1" >&2
        exit 1
        ;;

esac
