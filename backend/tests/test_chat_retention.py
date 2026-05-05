from service.infrastructure.messaging import tasks
from service.services.chat_worker.factory import ChatWorkerDependencyFactory
from tests.test_helpers import FakeConnector, FakeDBSession
from service import settings


def test_delete_old_chat_history_uses_config_and_commits(monkeypatch):
    fake_session = FakeDBSession()
    fake_connector = FakeConnector(fake_session)

    monkeypatch.setattr(
        ChatWorkerDependencyFactory,
        "create_pg_connector",
        lambda self, _config: fake_connector,
    )

    settings.config.chat_retention_days = 7
    res = tasks.delete_old_chat_history.run()

    assert res.get("status") == "ok"
    assert int(res.get("retention_days")) == 7

    executed_sql = "\n".join(s for s, _ in fake_session.executed)
    assert "DELETE FROM profile.chat_messages" in executed_sql
    assert "DELETE FROM profile.chat_threads" in executed_sql
    assert fake_session._committed is True
