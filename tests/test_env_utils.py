from orchestrator.utils import env_bool, env_float, env_int


def test_env_bool(monkeypatch):
    monkeypatch.setenv("BOOL_T", "true")
    monkeypatch.setenv("BOOL_F", "false")
    assert env_bool("BOOL_T") is True
    assert env_bool("BOOL_F") is False
    assert env_bool("MISSING", default=True) is True


def test_env_float(monkeypatch):
    monkeypatch.setenv("FLOAT_VAL", "0.42")
    monkeypatch.setenv("FLOAT_BAD", "abc")
    assert env_float("FLOAT_VAL") == 0.42
    assert env_float("FLOAT_BAD", default=1.0) == 1.0
    assert env_float("MISSING", default=None) is None


def test_env_int(monkeypatch):
    monkeypatch.setenv("INT_VAL", "7")
    monkeypatch.setenv("INT_BAD", "xyz")
    assert env_int("INT_VAL") == 7
    assert env_int("INT_BAD", default=5) == 5
    assert env_int("NONE", default=None) is None
