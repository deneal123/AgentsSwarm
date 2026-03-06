-- ===========================================================================
-- PostgreSQL Initialization Script for AgentsSwarm
-- Runs once on first container start via docker-entrypoint-initdb.d
-- Full schema is managed by Alembic migrations from the Orchestrator service
-- ===========================================================================

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation: uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- Cryptographic functions: crypt(), gen_salt()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram similarity for full-text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";    -- GIN indexes for scalar types

-- ─── Schema ──────────────────────────────────────────────────────────────────
-- Application objects live in the public schema (default)
-- Alembic will create all tables/indexes/constraints

-- ─── Enum Types (pre-created for Alembic compatibility) ──────────────────────
DO $$ BEGIN
  CREATE TYPE robot_status AS ENUM (
    'IDLE',
    'MOVING',
    'WORKING',
    'CHARGING',
    'OFFLINE',
    'ERROR',
    'EMERGENCY'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE task_status AS ENUM (
    'PENDING',
    'PLANNING',
    'ASSIGNED',
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE incident_severity AS ENUM (
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE user_role AS ENUM (
    'admin',
    'operator',
    'viewer'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE command_type AS ENUM (
    'MOVE',
    'PICK',
    'PLACE',
    'SCAN',
    'CHARGE',
    'WAIT',
    'PATROL',
    'EMERGENCY_STOP',
    'CUSTOM'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─── Logging ─────────────────────────────────────────────────────────────────
DO $$
BEGIN
  RAISE NOTICE 'AgentsSwarm PostgreSQL initialization complete.';
  RAISE NOTICE 'Extensions: uuid-ossp, pgcrypto, pg_trgm, btree_gin';
  RAISE NOTICE 'Enum types: robot_status, task_status, incident_severity, user_role, command_type';
  RAISE NOTICE 'Tables will be created by Alembic migrations (make migrate).';
END $$;
