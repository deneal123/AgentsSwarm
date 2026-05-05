import warnings
import pytest

from tests.test_helpers import FakeDBSession, FakeConnector, FakeRedis, FakeAsyncRedis


# Suppress noisy deprecation/warning messages during tests (pydantic/stopit/starlette)
def pytest_configure(config):
    warnings.filterwarnings(
        "ignore",
        message=r"Using extra keyword arguments on `Field` is deprecated.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"pkg_resources is deprecated as an API.*",
    )
    warnings.filterwarnings("ignore", category=UserWarning, module=r"stopit.*")
    warnings.filterwarnings("ignore", message=r".*HTTP_422_UNPROCESSABLE_ENTITY.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"starlette.*")


@pytest.fixture
def fake_connector_factory():
    """Return a factory that creates a FakeConnector for given reservation/quota rows.

    Usage: conn = fake_connector_factory(reservation=..., quota=...)
    """

    def _factory(reservation=None, quota=None, first_map_extra=None, all_map_extra=None):
        first_map = {}
        if reservation is not None:
            first_map["FROM profile.token_reservations"] = reservation
        if quota is not None:
            first_map["FROM profile.token_quotas"] = quota
        if first_map_extra:
            first_map.update(first_map_extra)

        session = FakeDBSession(first_map=first_map, all_map=all_map_extra or {})
        return FakeConnector(session)

    return _factory


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def fake_async_redis():
    return FakeAsyncRedis()


# Minimal pandas fallback for environments without pandas installed
try:
    import pandas as pd
except Exception:
    # Minimal fallback for tests that only need DataFrame with simple storage/printing
    class _DummyDataFrame:
        def __init__(self, data):
            self._data = data

        def __repr__(self):
            return f"_DummyDataFrame({self._data})"

    class _DummyPandasModule:
        def DataFrame(self, data):  # noqa: N802 - simple compatibility shim
            return _DummyDataFrame(data)

    pd = _DummyPandasModule()


@pytest.fixture
def fake_dask_client_tiny():
    class FakeClient:
        def scheduler_info(self):
            return {"workers": {"worker-1": {"memory_limit": 1024}}}

        def close(self):
            pass

    return FakeClient()


@pytest.fixture
def fake_dask_client_ok():
    class FakeClient:
        def scheduler_info(self):
            return {"workers": {"worker-1": {"memory_limit": 128 * 1024 * 1024}}}

        def close(self):
            pass

    return FakeClient()


@pytest.fixture
def fake_estimator_class():
    class FakeEstimator:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs

        def fit(self, X, y):
            self.fitted_pipeline_ = lambda x: 0
            self.evaluated_individuals_ = pd.DataFrame({"score": [0.5]})
            self.generations_completed_ = self.init_kwargs.get("generations", 1)
            return self

        def score(self, X, y):
            return 0.8

    return FakeEstimator
