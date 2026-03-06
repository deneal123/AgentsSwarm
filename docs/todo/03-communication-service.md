# TODO: Communication Service

Сервис-мост между MQTT (роботы) и RabbitMQ (микросервисы). Конфигурация EMQX и RabbitMQ, маршрутизация, ACL.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий communication_service.** Poetry-проект с зависимостями: paho-mqtt, pika, aio-pika, pydantic-settings, prometheus-client, structlog.

- [ ] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy, bandit.

- [ ] **Создать Dockerfile.** Multi-stage build, python:3.11-slim, healthcheck на /health.

- [ ] **Создать config.py.** Pydantic Settings: MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, RABBITMQ_URL, BRIDGE_RULES_PATH, LOG_LEVEL, JAEGER_ENDPOINT.

- [ ] **Создать main.py.** Entrypoint: запуск MQTT↔RabbitMQ bridge, FastAPI health endpoint, graceful shutdown.

---

## Этап 2 — Конфигурация EMQX

- [ ] **emqx.conf — основные настройки.** Listener TCP на 1883, WebSocket на 8083, Management API на 18083. Max connections: 10000. Keepalive: 60s.

- [ ] **emqx.conf — кластеризация.** Настройки для EMQX cluster: discovery strategy (static/dns/k8s), node name, cluster cookie.

- [ ] **acl.conf — правила доступа.** ACL по client_id паттернам: робот robot-* может publish в telemetry/{client_id}/# и subscribe на commands/{client_id}/#. Сервисы — полный доступ.

- [ ] **auth-mnesia.conf — аутентификация.** Username/password для роботов (per-robot credentials), superuser для внутренних сервисов. В production — интеграция с Redis/PostgreSQL auth backend.

- [ ] **Retained messages policy.** Настройка retained для: robot status (LWT), zone configurations, system announcements. TTL для retained messages.

- [ ] **Rate limiting.** EMQX rate limiting: max publish rate per client (100 msg/s для телеметрии), max subscribe rate.

---

## Этап 3 — Конфигурация RabbitMQ

- [ ] **rabbitmq.conf — основные настройки.** Default user, vhost, heartbeat: 30s, channel_max: 2048, management plugin enabled.

- [ ] **definitions.json — exchanges.** Предварительное создание exchanges: `commands` (topic), `events` (topic), `telemetry` (topic), `tasks` (direct), `dlx` (fanout — dead letter).

- [ ] **definitions.json — queues.** Создание очередей: `commands.user` (durable), `events.robot.*`, `tasks.planning`, `tasks.execution`, `tasks.monitoring`, `dlq` (dead letter queue).

- [ ] **definitions.json — bindings.** Привязки: `commands` exchange → `commands.user` по routing key `user.*`, `events` → `events.robot.*` по паттернам, `tasks` → task queues.

- [ ] **Quorum queues.** Для критических очередей (commands, tasks) — quorum queues вместо classic для гарантии HA и consistency.

- [ ] **TTL и dead-lettering.** Message TTL для очередей телеметрии (60s), dead-letter exchange для failed messages, retry exchange с TTL (exponential backoff).

---

## Этап 4 — MQTT → RabbitMQ Bridge (Uplink)

- [ ] **MQTT subscriber (bridge/mqtt_to_rabbitmq.py).** Подписка на MQTT-топики: `telemetry/#`, `events/#`, `ack/#`. Парсинг иерархии топика для определения robot_id и типа данных.

- [ ] **Маршрутизация uplink (bridge/router.py).** Правила: `telemetry/{robot_id}/+` → RabbitMQ exchange `telemetry` с routing key `robot.{robot_id}.{metric}`. `events/{robot_id}/+` → exchange `events` с routing key `robot.{robot_id}.{event_type}`.

- [ ] **Сериализация.** Преобразование MQTT payload (JSON/Protobuf) в формат RabbitMQ message с headers: source, timestamp, robot_id, content_type, correlation_id.

- [ ] **Backpressure.** При перегрузке RabbitMQ — буферизация в памяти (bounded queue), дропинг телеметрии (не команд), логирование dropped messages.

---

## Этап 5 — RabbitMQ → MQTT Bridge (Downlink)

- [ ] **RabbitMQ consumer (bridge/rabbitmq_to_mqtt.py).** Consume из очереди `commands.downlink`. Каждое сообщение содержит target_robot_id и command payload.

- [ ] **Маршрутизация downlink (bridge/router.py).** Правила: routing key `robot.{id}.command.{type}` → MQTT topic `commands/{robot_id}/{command_type}`. QoS 1 для команд, QoS 0 для конфигурации.

- [ ] **Acknowledgment.** Manual ack в RabbitMQ только после успешного publish в MQTT. При MQTT publish failure — nack + requeue с delay.

- [ ] **Priority commands.** MQTT publish с QoS 2 для emergency commands (stop, e-stop). Отдельная очередь `commands.priority` с prefetch_count=1.

---

## Этап 6 — Topic Manager

- [ ] **MQTT topics registry (mqtt/topics.py).** Описание всех MQTT-топиков, их QoS, payload schema, направление (uplink/downlink). Используется для валидации и документации.

- [ ] **RabbitMQ routing keys registry (rabbitmq/exchanges.py).** Описание всех exchanges, queues, bindings, routing key patterns. Используется для декларации и валидации.

- [ ] **ACL manager (mqtt/acl.py).** Генерация ACL-правил из реестра топиков и списка зарегистрированных роботов. Метод update_acl при регистрации нового робота.

---

## Этап 7 — Health и мониторинг

- [ ] **Health check EMQX (monitoring/health.py).** HTTP-запрос к EMQX Management API: /api/v5/status. Проверка: node alive, connected clients count, message rate.

- [ ] **Health check RabbitMQ (monitoring/health.py).** HTTP-запрос к RabbitMQ Management API: /api/healthchecks/node. Проверка: node alive, queue lengths, consumer counts.

---

## Этап 8 — Тесты

- [ ] **conftest.py.** Фикстуры: mock EMQX (paho-mqtt в test mode), testcontainers RabbitMQ, sample MQTT messages, sample RabbitMQ messages.

- [ ] **Unit: router.** Тесты маршрутизации: MQTT topic → RabbitMQ routing key (uplink), RabbitMQ routing key → MQTT topic (downlink). Edge cases: unknown topics, malformed payloads.

- [ ] **Unit: serialization.** Тесты конвертации: JSON ↔ RabbitMQ message headers. Protobuf encoding/decoding.

- [ ] **Integration: bridge.** Полный цикл: publish MQTT → bridge → consume RabbitMQ (uplink). Publish RabbitMQ → bridge → subscribe MQTT (downlink).

- [ ] **Integration: EMQX client.** Подключение, подписка, publish, retained messages, LWT с реальным EMQX (testcontainers).

- [ ] **Integration: RabbitMQ client.** Exchange declare, queue bind, publish, consume, ack/nack с реальным RabbitMQ (testcontainers).
