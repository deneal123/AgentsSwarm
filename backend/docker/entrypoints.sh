#!/usr/bin/env bash

# Function to ensure database exists
ensure_database_exists() {
    echo "Checking if database '${PG__DB}' exists..."

    # Build connection string for postgres database (always exists)
    PGPASSWORD="${PG__PASSWORD}" psql -h "${PG__HOST}" -p "${PG__PORT}" -U "${PG__USER}" -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '${PG__DB}'" | grep -q 1

    if [ $? -ne 0 ]; then
        echo "Database '${PG__DB}' does not exist. Creating..."
        PGPASSWORD="${PG__PASSWORD}" psql -h "${PG__HOST}" -p "${PG__PORT}" -U "${PG__USER}" -d postgres -c \
            "CREATE DATABASE ${PG__DB};"
        echo "Database '${PG__DB}' created successfully."
    else
        echo "Database '${PG__DB}' already exists."
    fi
}

case "$1" in
    "bash")
        echo "Starting bash ..."
        exec bash -c "$2"
        ;;

    "zombie")
        echo "Starting zombie ..."
        exec tail -f /dev/null
        ;;


    "server")
        echo "Starting server ..."
        # Ensure database exists before running migrations
        ensure_database_exists
        echo "Preparing database for migrations"
        # Ensure alembic_version exists and its version_num column can hold descriptive
        # revision identifiers. Some repositories use long descriptive revision ids
        # that exceed the default varchar(32). We will (1) create the table if it
        # doesn't exist, and (2) alter the column type if it does. Best-effort:
        # ignore errors but attempt both operations to avoid asyncpg truncation
        # errors during alembic upgrades in dev environments.
        PSQL_BASE=( -h "${PG__HOST}" -p "${PG__PORT}" -U "${PG__USER}" -d "${PG__DB}" -c )
        # Create table if missing with wide column
        if PGPASSWORD="${PG__PASSWORD}" psql "${PSQL_BASE[@]}" "CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(255) NOT NULL);"; then
            echo "Created alembic_version table if missing (or it already existed)"
        else
            echo "Warning: failed to create alembic_version table (continuing)" >&2
        fi

        # Ensure column is wide enough when table already existed
        if PGPASSWORD="${PG__PASSWORD}" psql "${PSQL_BASE[@]}" "ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE varchar(255);"; then
            echo "Ensured alembic_version.version_num column wide enough"
        else
            echo "Warning: could not alter alembic_version column or it already fits" >&2
        fi

        echo "Running database migrations (alembic upgrade heads)"
        # Use 'heads' to apply all branch heads when multiple heads exist.
        # This is a pragmatic choice for dev environments. For production,
        # prefer creating a merge migration to keep history linear.
        if ! alembic -c /dude/alembic/alembic.ini upgrade heads; then
            echo "Alembic migration failed" >&2
            exit 1
        fi
        # Enable reload in dev if requested
        RELOAD_ARGS=""
        if [ "${SERVICE_DEBUG}" = "1" ] || [ "${UVICORN_RELOAD}" = "1" ]; then
            echo "Starting in reload mode"
            RELOAD_ARGS="--reload"
        fi
        # Use direct app import for reload compatibility
        exec python -m uvicorn service.main:app \
            --host 0.0.0.0 \
            --port ${SERVICE_SERVER_PORT:-8000} \
            --workers ${UVICORN_WORKERS:-1} \
            --proxy-headers \
            ${RELOAD_ARGS}
        ;;

    *)
        echo "Executing custom command: $@"
        exec "$@"
        ;;

esac
