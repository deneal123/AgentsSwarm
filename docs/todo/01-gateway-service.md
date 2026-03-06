# TODO: Gateway Service

API-шлюз на FastAPI — единая точка входа для фронтенда. REST API, WebSocket, аутентификация, маршрутизация к внутренним сервисам.

---

## Этап 1 — Инициализация проекта

- [x] **Создать репозиторий gateway_service.** Poetry-проект `services/gateway_service/`, `pyproject.toml`: fastapi, uvicorn[standard], pydantic-settings, python-jose[cryptography], passlib[bcrypt], aio-pika, redis[hiredis], grpcio, httpx, structlog, opentelemetry-*, prometheus-client. Dev: pytest, ruff, mypy, bandit, fakeredis.

- [x] **Настроить .pre-commit-config.yaml.** Хуки: `pre-commit-hooks` (trailing-whitespace, end-of-file, check-yaml/toml, detect-private-key, no-commit-to-branch:main), `ruff` (lint --fix + format), `mypy`, `bandit`.

- [x] **Создать Dockerfile.** Multi-stage: `builder` (poetry install --only=main) → `runtime` (python:3.11-slim, UID 1001, `HEALTHCHECK curl /health`). `PYTHONPATH=/app/src`. CMD: uvicorn с uvloop+httptools.

- [x] **Создать config.py (Pydantic Settings).** `Settings(BaseSettings)` с `@lru_cache`. Секции: app (name, version, env, debug, log_level), JWT (secret ≥32 chars, algorithm, expire), Redis (url, pool), RabbitMQ (url, exchanges), gRPC (host:port, deadline), CORS, Rate Limiting, WebSocket, Observability (OTLP, Jaeger, sample_rate). `.env.example` создан.

- [x] **Создать main.py с lifespan.** `create_app()` фабрика. `lifespan`: startup → `RedisClient.connect()`, `RabbitMQPublisher.connect()`; shutdown → graceful close. Middleware: CORS, TrustedHost (prod), request logging (structlog). Роутеры: health, api_v1_router (/api/v1), ws_router (/ws). Metrics + Tracing setup по флагам.

---

## Этап 2 — Аутентификация и авторизация

- [x] **JWT модуль (auth/jwt.py).** Функции create_access_token и verify_token. Алгоритм HS256, configurable expiration. Payload: user_id, role, exp, jti (UUID4 для blacklist), token_type.

- [x] **Auth middleware (auth/middleware.py).** FastAPI dependency get_current_user: извлечение токена из Authorization header или `?token=` query param (WebSocket), валидация, проверка blacklist в Redis (fail-open), возврат UserContext.

- [x] **RBAC (auth/permissions.py).** Декоратор/dependency require_role(*roles), require_min_role(min_role). Роли: VIEWER < ROBOT < OPERATOR < SUPERVISOR < ADMIN. Shortcuts: require_admin, require_operator, require_supervisor, require_authenticated.

- [x] **Auth schemas (auth/schemas.py).** Pydantic-модели: LoginRequest, TokenResponse, UserContext, RegisterRequest (с валидатором пароля), RefreshRequest, UserUpdateRequest, TokenPayload. UserRole enum, ROLE_HIERARCHY dict.

- [x] **Auth endpoints (api/v1/users.py).** POST /auth/login, POST /auth/register (201), GET /auth/me, PUT /auth/me, POST /auth/refresh (token rotation + blacklist), POST /auth/logout (204, revoke refresh token).

---

## Этап 3 — REST API endpoints

- [x] **Роутер v1 (api/v1/router.py).** Подключены все роутеры: users (auth), robots, tasks, zones, chat, telemetry с соответствующими prefix и tags.

- [x] **Robots CRUD (api/v1/robots.py).** GET /robots (пагинация + фильтр status/zone_id/has_task), GET /robots/{id}, GET /robots/{id}/telemetry. Заглушки gRPC помечены TODO (Этап 6).

- [x] **Tasks CRUD (api/v1/tasks.py).** GET /tasks (фильтр status/robot_id/zone_id), GET /tasks/{id}, POST /tasks → publish RabbitMQ (routing_key: task.create), PUT /tasks/{id}/cancel → publish RabbitMQ (routing_key: task.cancel). Требует OPERATOR+.

- [x] **Zones CRUD (api/v1/zones.py).** GET /zones, GET /zones/{id}, POST /zones (OPERATOR+), PUT /zones/{id} (OPERATOR+), DELETE /zones/{id} (ADMIN). In-memory store до подключения БД (Этап 6).

- [x] **Chat REST (api/v1/chat.py).** POST /chat/message (202 Accepted) — publish в RabbitMQ routing_key `commands.user`, возврат CommandAck с task_id. Fail-open в dev-режиме без RabbitMQ.

- [x] **Telemetry (api/v1/telemetry.py).** GET /telemetry/{robot_id} — query params: from, to (ISO 8601), resolution (raw/10s/1m/5m/15m/1h/6h/1d). Валидация диапазона (max 30 дней). TODO InfluxDB (Этап 6).

---

## Этап 4 — Pydantic Schemas

- [x] **Robot schemas (schemas/robot.py).** RobotSummary, RobotDetail, RobotTelemetry, RobotListFilters, Position, SensorDataItem, RobotEventItem, RobotStatus enum.

- [x] **Task schemas (schemas/task.py).** TaskCreate, TaskSummary, TaskDetail, TaskListFilters, TaskCancel, TaskStatus enum.

- [x] **Zone schemas (schemas/zone.py).** ZoneCreate, ZoneUpdate, ZoneDetail, ZoneSummary, ZoneBounds.

- [x] **Chat schemas (schemas/chat.py).** ChatMessage, CommandAck (task_id + trace_id), ChatResponse (streaming-compatible: is_final flag).

- [x] **Telemetry schemas (schemas/telemetry.py).** TelemetryPoint, TelemetryHistory, TelemetryResolution enum (raw/10s/1m/5m/15m/1h/6h/1d).

- [x] **Common schemas (schemas/common.py).** PaginationParams (offset/limit props), PaginatedResponse[T] (Generic), pagination_params Depends-фабрика, ErrorResponse, MessageResponse.

---

## Этап 5 — WebSocket

- [x] **WebSocket Manager (ws/manager.py).** `ConnectionManager`: `_connections: dict[conn_id, _Connection]`, `_user_index: dict[user_id, set[conn_id]]`. Методы: connect, disconnect, disconnect_user, send_to_user, send_to_connection, broadcast (с фильтром по каналу), ping_all, evict_stale, update_pong, connection_info. Синглтон `get_connection_manager()`.

- [x] **WebSocket роутер (ws/router.py).** `WS /ws/chat`, `WS /ws/telemetry`, `WS /ws/notifications`. Аутентификация через `?token=<access_jwt>`. Каждый маршрут делегирует в соответствующий handler.

- [x] **Chat handler (ws/handlers.py).** Приём `{"type":"message","text":"..."}` → publish RabbitMQ `commands.user` → подписка на Redis `chat.responses.{user_id}` → стриминг chunk/reply клиенту. Ack с task_id после publish.

- [x] **Telemetry handler (ws/handlers.py).** `subscribe/unsubscribe` по robot_ids. Каждый робот — отдельная asyncio.Task на Redis Pub/Sub `telemetry.{robot_id}`. Динамическая подписка/отписка без переподключения.

- [x] **Notification handler (ws/handlers.py).** Pattern subscribe `notifications.*` (Redis). Фильтрация личных уведомлений по `user_id`. Пересылка task_update, robot_event, incident.

- [x] **Heartbeat.** Фоновая задача `_heartbeat_background` в lifespan: ping каждые `ws_heartbeat_seconds` сек, `evict_stale` при превышении `ws_disconnect_timeout_seconds`. Клиент отвечает `{"type":"pong"}` → `manager.update_pong(conn_id)`.

---

## Этап 6 — Интеграционные клиенты

- [x] **RabbitMQ Publisher (services/rabbitmq.py).** Async publisher через aio-pika. Методы: publish_command(queue, message), publish_event(exchange, routing_key, message). Reconnect при потере соединения.

- [x] **Redis Client (services/redis_client.py).** Async redis.asyncio клиент. Методы: get/set с TTL, pub/sub subscribe/publish, connection pool. Используется для кэша и real-time events.

- [x] **gRPC Client к Orchestrator (services/grpc_client.py).** Клиент для прямых вызовов: get_robot_state, get_task_status, submit_priority_command. Timeout, retry, circuit breaker.

- [x] **Rate Limiter (services/rate_limiter.py).** Token bucket на Redis (Lua-скрипт, атомарно). Лимиты по user_id: 100 req/min для REST, 30 msg/min для chat. Configurable через settings. Fail-open при недоступном Redis.

---

## Этап 7 — Middleware

- [x] **CORS middleware.** Настраиваемые origins из config (CORS_ORIGINS). Dev: `allow_origins=["*"]`, `allow_credentials=False`. Prod: только явно заданные `settings.cors_origins` с `allow_credentials=True`. Реализовано в `create_app()` через ветку `is_development`.

- [x] **Tracing middleware (OpenTelemetry).** `monitoring/tracing.py`: `setup_tracing(app, endpoint, sample_rate, service_name, service_version)`. OTLP gRPC экспортер, `TraceIdRatioBased` sampler, W3C `TraceContextTextMapPropagator` (заголовки `traceparent`/`tracestate`), `FastAPIInstrumentor.instrument_app()`. Публичный хелпер `get_trace_id() → str | None` для логирования и заголовков ответа.

- [x] **Structured logging middleware.** `middleware/logging.py`: `RequestLoggingMiddleware(BaseHTTPMiddleware)`. Генерирует `X-Request-ID`, привязывает structlog contextvars (`request_id`, `http_method`, `http_path`). Логирует итоговую строку `http.request` с `status_code`, `duration_ms`, `trace_id`, `user_id`, `client_ip`. Добавляет `X-Request-ID` и `X-Trace-ID` в ответ. Служебные пути (`/health`, `/ready`, `/metrics`) пропускаются.

- [x] **Global error handler.** `_register_exception_handlers(app)` в `main.py`. Маппинг: `HTTPException` → проброс detail/headers, `AuthError` → 401 + WWW-Authenticate, `PermissionDeniedError` → 403, `UserNotFoundError` → 404, `UserAlreadyExistsError` → 409, `RequestValidationError` → 422 + details, `Exception` → 500 + trace_id. Все ответы — `ORJSONResponse` с `error_code` + `message`.

---

## Этап 8 — Тесты

- [ ] **conftest.py.** Фикстуры: TestClient (async), mock Redis, mock RabbitMQ, mock gRPC, test user tokens (operator, admin).

- [ ] **Unit: auth.** Тесты create_token, verify_token, expired token, invalid token, RBAC role checks.

- [ ] **Unit: schemas.** Валидация всех Pydantic-моделей: обязательные поля, типы, enum values, пагинация.

- [ ] **Unit: rate limiter.** Тесты token bucket: allowed requests, rate exceeded, TTL reset.

- [ ] **Integration: REST API.** Тесты CRUD для robots, tasks, zones, chat. Проверка auth, пагинации, фильтрации, ошибок.

- [ ] **Integration: WebSocket.** Тесты подключения, аутентификации через WS, приём/отправка сообщений, heartbeat, disconnect.
