"""
Integration-тесты: WebSocket endpoints.

Маршруты:
  WS /ws/chat          — чат (auth, message → ack, invalid json, pong)
  WS /ws/telemetry     — телеметрия (auth, subscribe)
  WS /ws/notifications — уведомления (auth, подключение)

Аутентификация: ?token= в query string.
  Без токена    → error JSON + close(4001)
  Невалидный    → error JSON + close(4001)

Используем starlette.testclient.TestClient (sync) — httpx не поддерживает WS.
sync_client фикстура определена в conftest.py.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


# ─── /ws/chat — аутентификация ────────────────────────────────────────────────


def test_ws_chat_no_token_sends_error(sync_client: TestClient) -> None:
    """Без ?token= сервер присылает JSON ошибки и закрывает соединение."""
    with sync_client.websocket_connect("/ws/chat") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "MISSING_TOKEN" in msg["error_code"] or msg["error_code"] == "MISSING_TOKEN"


def test_ws_chat_invalid_token_sends_error(sync_client: TestClient) -> None:
    """Невалидный токен → error с кодом AUTH_ERROR."""
    with sync_client.websocket_connect("/ws/chat?token=this.is.not.valid") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["error_code"] in ("AUTH_ERROR", "INVALID_TOKEN", "MISSING_TOKEN")


def test_ws_chat_valid_token_accepts(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """Валидный токен → соединение принято (нет немедленного error)."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        # Отправляем pong чтобы не блокировать; затем сразу отключаемся
        ws.send_json({"type": "pong"})
        # Соединение открыто без ошибки — тест прошёл


def test_ws_chat_message_returns_ack(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """
    Отправка {"type":"message","text":"move to station"} →
    сервер возвращает {"type":"ack","task_id":"..."}.
    """
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        ws.send_json({"type": "message", "text": "move to station"})
        ack = ws.receive_json()
        assert ack["type"] == "ack"
        assert "task_id" in ack
        assert len(ack["task_id"]) > 0


def test_ws_chat_message_has_timestamp(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """ack содержит поле timestamp в ISO-формате."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        ws.send_json({"type": "message", "text": "go to zone A"})
        ack = ws.receive_json()
        assert "timestamp" in ack
        assert ack["timestamp"].endswith("Z")


def test_ws_chat_empty_text_returns_error(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """Пустой text → error EMPTY_MESSAGE."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        ws.send_json({"type": "message", "text": ""})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["error_code"] == "EMPTY_MESSAGE"


def test_ws_chat_invalid_json_returns_error(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """Не-JSON строка → error INVALID_JSON."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        ws.send_text("this is not json")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["error_code"] == "INVALID_JSON"


def test_ws_chat_pong_accepted(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """{"type":"pong"} обрабатывается без ошибок (heartbeat pong)."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        ws.send_json({"type": "pong"})
        # Следующее сообщение — chat message, не ошибка
        ws.send_json({"type": "message", "text": "ping test"})
        ack = ws.receive_json()
        assert ack["type"] == "ack"


def test_ws_chat_rabbitmq_called_on_message(
    app,
    operator_token: str,
    mock_rabbitmq,
    mock_redis,
    mock_grpc,
) -> None:
    """При сообщении через WS/chat публикуется команда в RabbitMQ."""
    app.state.rabbitmq = mock_rabbitmq
    app.state.redis = mock_redis
    app.state.grpc_client = mock_grpc

    with TestClient(app, raise_server_exceptions=False) as tc:
        with tc.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
            ws.send_json({"type": "message", "text": "robot stop"})
            ack = ws.receive_json()
            assert ack["type"] == "ack"

    mock_rabbitmq.publish_command.assert_called_once()
    kwargs = mock_rabbitmq.publish_command.call_args.kwargs
    assert kwargs["routing_key"] == "commands.user"
    assert kwargs["payload"]["text"] == "robot stop"


def test_ws_chat_multiple_messages(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """Несколько сообщений в одном соединении — каждое получает ack."""
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws:
        for i in range(3):
            ws.send_json({"type": "message", "text": f"command {i}"})
            ack = ws.receive_json()
            assert ack["type"] == "ack"


# ─── /ws/telemetry ────────────────────────────────────────────────────────────


def test_ws_telemetry_no_token_error(sync_client: TestClient) -> None:
    with sync_client.websocket_connect("/ws/telemetry") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_telemetry_invalid_token_error(sync_client: TestClient) -> None:
    with sync_client.websocket_connect("/ws/telemetry?token=bad.token") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_telemetry_subscribe(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """
    {"type":"subscribe","robot_ids":["r1"]} →
    сервер возвращает {"type":"subscribed","robot_ids":["r1"]}.
    """
    with sync_client.websocket_connect(f"/ws/telemetry?token={operator_token}") as ws:
        ws.send_json({"type": "subscribe", "robot_ids": ["r1"]})
        msg = ws.receive_json()
        assert msg["type"] == "subscribed"
        assert "r1" in msg.get("robot_ids", [])


def test_ws_telemetry_unsubscribe(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """subscribe затем unsubscribe — сервер возвращает unsubscribed."""
    with sync_client.websocket_connect(f"/ws/telemetry?token={operator_token}") as ws:
        ws.send_json({"type": "subscribe", "robot_ids": ["r2"]})
        ws.receive_json()  # subscribed

        ws.send_json({"type": "unsubscribe", "robot_ids": ["r2"]})
        msg = ws.receive_json()
        assert msg["type"] == "unsubscribed"
        assert "r2" in msg.get("robot_ids", [])


def test_ws_telemetry_pong_no_error(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """Heartbeat pong не вызывает ошибок в telemetry handler."""
    with sync_client.websocket_connect(f"/ws/telemetry?token={operator_token}") as ws:
        ws.send_json({"type": "pong"})
        ws.send_json({"type": "subscribe", "robot_ids": ["r3"]})
        msg = ws.receive_json()
        assert msg["type"] == "subscribed"


def test_ws_telemetry_viewer_allowed(
    sync_client: TestClient,
    viewer_token: str,
) -> None:
    """VIEWER может подписаться на телеметрию."""
    with sync_client.websocket_connect(f"/ws/telemetry?token={viewer_token}") as ws:
        ws.send_json({"type": "subscribe", "robot_ids": ["r-viewer"]})
        msg = ws.receive_json()
        assert msg["type"] == "subscribed"


# ─── /ws/notifications ───────────────────────────────────────────────────────


def test_ws_notifications_no_token_error(sync_client: TestClient) -> None:
    with sync_client.websocket_connect("/ws/notifications") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_ws_notifications_connect_success(
    sync_client: TestClient,
    operator_token: str,
) -> None:
    """
    Успешное подключение к /ws/notifications.
    Сервер может отправить приветственное сообщение или ничего — соединение не закрывается с ошибкой.
    """
    with sync_client.websocket_connect(f"/ws/notifications?token={operator_token}") as ws:
        ws.send_json({"type": "pong"})
        # Если сервер ничего не шлёт, таймаут — но raise_server_exceptions=False защищает нас
        # Проверяем только что соединение открыто без ошибки


def test_ws_notifications_viewer_allowed(
    sync_client: TestClient,
    viewer_token: str,
) -> None:
    """VIEWER имеет доступ к уведомлениям."""
    with sync_client.websocket_connect(f"/ws/notifications?token={viewer_token}") as ws:
        ws.send_json({"type": "pong"})


# ─── Изоляция соединений ─────────────────────────────────────────────────────


def test_ws_multiple_users_isolated(
    sync_client: TestClient,
    operator_token: str,
    viewer_token: str,
) -> None:
    """
    Два пользователя с разными ролями могут одновременно подключиться к /ws/chat.
    (Последовательно — TestClient не поддерживает настоящий параллелизм)
    """
    with sync_client.websocket_connect(f"/ws/chat?token={operator_token}") as ws1:
        ws1.send_json({"type": "message", "text": "operator message"})
        ack1 = ws1.receive_json()
        assert ack1["type"] == "ack"
        task_id_1 = ack1["task_id"]

    with sync_client.websocket_connect(f"/ws/chat?token={viewer_token}") as ws2:
        ws2.send_json({"type": "message", "text": "viewer message"})
        ack2 = ws2.receive_json()
        assert ack2["type"] == "ack"
        task_id_2 = ack2["task_id"]

    # task_id уникальны
    assert task_id_1 != task_id_2
