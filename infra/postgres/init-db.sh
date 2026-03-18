#!/bin/bash
set -e

# This script runs on PostgreSQL container startup
# It ensures the database exists (POSTGRES_DB is auto-created, but this handles edge cases)

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    -- Create database if not exists (idempotent)
    SELECT 'CREATE DATABASE ${POSTGRES_DB}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\gexec

    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};
EOSQL

echo "Database '${POSTGRES_DB}' is ready."
