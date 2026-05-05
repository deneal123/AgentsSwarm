import os
import pytest

try:
    import psycopg2
except Exception:  # pragma: no cover - dependency may be absent in unit CI
    psycopg2 = None

try:
    import redis as redis_lib
except Exception:  # pragma: no cover
    redis_lib = None


@pytest.mark.integration
def test_postgres_and_redis_connectivity():
    run_integration = os.getenv("RUN_INTEGRATION", "0")
    if run_integration != "1":
        pytest.skip("Integration tests are disabled (set RUN_INTEGRATION=1 to enable)")

    assert psycopg2 is not None, "psycopg2 is not installed"
    assert redis_lib is not None, "redis client is not installed"

    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Connect to Postgres
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    val = cur.fetchone()[0]
    cur.close()
    conn.close()
    assert val == 1

    # Connect to Redis
    r = redis_lib.from_url(redis_url)
    pong = r.ping()
    assert pong is True
