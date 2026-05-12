import re
from pathlib import Path


def _service_py_files():
    base = Path(__file__).resolve().parents[1] / "service"
    return list(base.rglob("*.py"))


def test_no_redis_publish_or_pubsub_usage():
    """Ensure service code does not directly call Redis Pub/Sub publish() or use PubSub API."""
    for p in _service_py_files():
        txt = p.read_text(encoding="utf-8", errors="replace")
        # Check for direct Redis client publish calls (not port method calls)
        assert "redis.publish(" not in txt, f"Found redis.publish( usage in {p}"
        assert "_client.publish(" not in txt, f"Found _client.publish( usage in {p}"
        assert "PubSub" not in txt, f"Found PubSub usage in {p}"
        assert re.search(r"\bpubsub\b", txt, re.IGNORECASE) is None, f"Found pubsub reference in {p}"


def test_uses_redis_streams_xadd():
    """Check that Redis Streams (xadd) are used somewhere in service code (expected)."""
    found = False
    for p in _service_py_files():
        if "xadd(" in p.read_text():
            found = True
            break
    assert found, "No usage of Redis Streams xadd() found in service code"
