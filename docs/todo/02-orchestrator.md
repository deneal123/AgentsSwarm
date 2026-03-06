# TODO: Orchestrator

Центральный микросервис — «мозг» системы. LangGraph для управления процессами, OpenAI Agents SDK для мультиагентной логики, Celery для распределённых задач.

---

## Этап 1 — Инициализация проекта

- [ ] **Создать репозиторий orchestrator.** Poetry-проект с зависимостями: celery[redis], langgraph, langgraph-checkpoint-postgres, langgraph-checkpoint-redis, openai-agents, paho-mqtt, pika, sqlalchemy[asyncio], asyncpg, redis, grpcio, influxdb3-python, neo4j, pydantic-settings.

- [ ] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy (strict mode), bandit, trailing whitespace.

- [ ] **Создать Dockerfile.** Multi-stage build. Два entrypoint: основной сервер (gRPC + health API) и Celery worker.

- [ ] **Создать Dockerfile.celery.** Отдельный образ для Celery workers с тем же кодом, но другим entrypoint (celery -A ... worker).

- [ ] **Создать config.py.** Pydantic Settings: RABBITMQ_URL, REDIS_URL, POSTGRES_URL, MQTT_BROKER, MQTT_PORT, TRITON_URL, VLLM_URL, SMOLVLA_URL, INFLUXDB_URL, INFLUXDB_TOKEN, NEO4J_URI, NEO4J_AUTH, LOG_LEVEL, JAEGER_ENDPOINT.

- [ ] **Создать main.py.** Entrypoint: запуск gRPC-сервера, FastAPI health endpoint (/health, /ready), инициализация подключений в lifespan.

---

## Этап 2 — SQLAlchemy модели и миграции

- [ ] **Base (models/base.py).** declarative_base(), общий базовый класс с полями id (UUID), created_at, updated_at.

- [ ] **Robot model (models/robot.py).** Таблица robots: id, model, serial_number, status (RobotStatus enum), battery_level, zone_id (FK → zones), last_seen, config (JSONB).

- [ ] **Task model (models/task.py).** Таблица tasks: id, type, status (TaskStatus enum), assigned_robot_id (FK), creator_id (FK → users), priority, params (JSONB), result (JSONB), created_at, started_at, finished_at.

- [ ] **User model (models/user.py).** Таблица users: id, name, email, role (UserRole enum), password_hash, is_active, created_at.

- [ ] **Incident model (models/incident.py).** Таблица incidents: id, robot_id (FK), description, severity (enum), resolved_at, resolution_notes, created_at.

- [ ] **AuditLog model (models/audit.py).** Таблица audit_logs: id, actor_id (FK → users), action, target_type, target_id, details (JSONB), timestamp.

- [ ] **Zone model (models/zone.py).** Таблица zones: id, name, boundaries (JSONB), type, max_robots.

- [ ] **ModelVersion model (models/model_version.py).** Таблица model_versions: id, model_name, version, minio_path, status, deployed_at, metrics (JSONB).

- [ ] **Alembic — инициализация.** alembic init, настройка env.py для async (asyncpg), начальная миграция с созданием всех таблиц.

- [ ] **Postgres service (services/postgres.py).** create_async_engine, async_sessionmaker, dependency get_session. Connection pool: pool_size=10, max_overflow=20, pool_pre_ping=True.

---

## Этап 3 — Celery

- [ ] **Celery app (celery_app/app.py).** Создание Celery instance с broker=RABBITMQ_URL, backend=REDIS_URL. Конфигурация: task_serializer=json, result_expires=3600, worker_prefetch_multiplier=1.

- [ ] **Planning tasks (celery_app/tasks/planning.py).** Задачи: plan_from_command (NL-команда → план через LangGraph), replan_task (перепланирование при неудаче).

- [ ] **Execution tasks (celery_app/tasks/execution.py).** Задачи: execute_robot_command (отправка MQTT-команды роботу), monitor_task_progress (polling статуса), handle_task_timeout.

- [ ] **Monitoring tasks (celery_app/tasks/monitoring.py).** Задачи: check_robot_health (проверка LWT/heartbeat), aggregate_telemetry (агрегация данных из Redis в InfluxDB).

- [ ] **Maintenance tasks (celery_app/tasks/maintenance.py).** Периодические задачи: cleanup_expired_sessions, rotate_feature_store, sync_robot_registry.

- [ ] **Celery Beat schedules (celery_app/schedules.py).** Расписание: check_robot_health каждые 30 секунд, aggregate_telemetry каждые 60 секунд, cleanup каждые 6 часов.

---

## Этап 4 — LangGraph Engine

- [ ] **SwarmState (graph/state.py).** TypedDict с полями: user_command, parsed_intent, plan, subtasks (list), assignments (dict), execution_status (dict), robot_states (dict), messages (list), error. Reducer-функции для append-полей.

- [ ] **Main Graph (graph/main_graph.py).** StateGraph с узлами: intake → planning → assignment → execution → evaluation → reporting. Conditional edges: routing по типу задачи, retry при evaluation fail.

- [ ] **Intake node (graph/nodes/intake.py).** Классификация команды: простая (прямое выполнение) / сложная (требует планирования) / мультироботная (требует координации). Обращение к vLLM для NLU.

- [ ] **Planning node (graph/nodes/planning.py).** Генерация плана через vLLM: декомпозиция на подзадачи, определение порядка, зависимостей, ресурсов. Сохранение плана в state.

- [ ] **Assignment node (graph/nodes/assignment.py).** Назначение роботов через Send API (один подграф на каждого робота). ResourceManager выбирает оптимального робота по: статус, батарея, расстояние, capabilities.

- [ ] **Execution node (graph/nodes/execution.py).** Отправка команд роботам через MQTT, ожидание ack. Timeout с retry. Обновление execution_status в state.

- [ ] **Evaluation node (graph/nodes/evaluation.py).** Оценка результата выполнения. Если неуспех — conditional edge на replanning (макс. 3 попытки). Если успех — на reporting.

- [ ] **Reporting node (graph/nodes/reporting.py).** Формирование ответа пользователю, публикация в Redis Pub/Sub для доставки через Gateway WebSocket.

- [ ] **Navigation subgraph (graph/subgraphs/navigation.py).** Подграф для навигационных задач: move_to → wait_arrival → verify_position.

- [ ] **Manipulation subgraph (graph/subgraphs/manipulation.py).** Подграф для манипуляционных задач: approach → detect_object → plan_grasp (SmolVLA) → execute_grasp → verify.

- [ ] **Checkpointing — PostgresSaver.** Настройка langgraph-checkpoint-postgres для сохранения state в PostgreSQL. Recovery при перезапуске Orchestrator.

- [ ] **Checkpointing — RedisSaver.** RedisSaver для быстрого чекпоинтинга высокочастотных графов (мониторинг). Fallback на PostgresSaver.

- [ ] **Long-term memory — PostgresStore.** Хранение успешных планов с эмбеддингами для семантического поиска. При новой команде — поиск похожих прошлых планов.

---

## Этап 5 — OpenAI Agents SDK

- [ ] **SwarmContext (agents/context.py).** RunContextWrapper с полями: redis_client, postgres_session, mqtt_client, grpc_clients (triton, vllm, smolvla), user_context, trace_id.

- [ ] **Planner Agent (agents/planner_agent.py).** Agent с instructions для планирования, tools: query_robot_states, query_zone_info, search_similar_plans. Output_type: Plan (structured).

- [ ] **Executor Agent (agents/executor_agent.py).** Agent с instructions для выполнения, tools: send_mqtt_command, call_smolvla, query_triton_detection. Handoff к Safety Agent при опасных действиях.

- [ ] **Monitor Agent (agents/monitor_agent.py).** Agent для отслеживания выполнения. Tools: get_task_status, get_robot_position, check_deadline. Handoff к Planner при необходимости перепланирования.

- [ ] **Safety Agent (agents/safety_agent.py).** Agent с guardrails для проверки безопасности. Tools: check_collision_risk, verify_zone_boundaries, check_battery_level. Может выполнить emergency_stop.

- [ ] **Robot tools (agents/tools/robot_tools.py).** Function tools: send_move_command, send_stop_command, send_grasp_command, get_robot_state, get_robot_capabilities.

- [ ] **Query tools (agents/tools/query_tools.py).** Function tools: query_feature_store (Redis), query_telemetry_history (InfluxDB), query_spatial_graph (Neo4j), query_task_history (PostgreSQL).

- [ ] **Vision tools (agents/tools/vision_tools.py).** Function tools: detect_objects (Triton gRPC), analyze_scene (vLLM multimodal), predict_action (SmolVLA gRPC).

- [ ] **Input guardrails (agents/guardrails/input_guards.py).** Проверка входной команды: длина, язык, наличие запрещённых паттернов. Tripwire при подозрении на injection.

- [ ] **Output guardrails (agents/guardrails/output_guards.py).** Проверка плана: все назначенные роботы существуют и доступны, зоны валидны, команды в допустимом списке.

- [ ] **Safety guardrails (agents/guardrails/safety_guards.py).** Tool-барьеры: проверка безопасности перед каждой MQTT-командой. Tripwire при emergency_stop.

- [ ] **Handoffs (agents/handoffs.py).** Правила передачи: Planner → Executor (план готов), Executor → Safety (опасное действие), Monitor → Planner (перепланирование), любой → Safety (emergency).

---

## Этап 6 — Менеджеры

- [ ] **TaskManager (managers/task_manager.py).** CRUD задач в PostgreSQL. Жизненный цикл: PENDING → ASSIGNED → IN_PROGRESS → COMPLETED/FAILED. Публикация событий в Redis Pub/Sub при смене статуса.

- [ ] **ResourceManager (managers/resource_manager.py).** Реестр роботов из Redis Feature Store. Алгоритм назначения: фильтрация по capabilities → сортировка по (расстояние, батарея, загрузка) → выбор оптимального.

- [ ] **CoordinationManager (managers/coordination.py).** Координация мультироботных задач: распределение зон поиска, избежание столкновений (mutual exclusion zones), синхронизация этапов.

---

## Этап 7 — Интеграционные клиенты

- [ ] **MQTT Client (services/mqtt_client.py).** paho-mqtt async wrapper. Методы: publish_command(robot_id, command), subscribe_events(callback), subscribe_telemetry(robot_id, callback). Auto-reconnect, LWT.

- [ ] **RabbitMQ Client (services/rabbitmq.py).** Consumer для `commands.user` queue. Publisher для событий. Celery broker integration через ту же connection.

- [ ] **Redis Client (services/redis_client.py).** redis.asyncio. Методы: get/set Feature Store, pub/sub для events, TimeSeries для краткосрочных метрик, pipeline для batch updates.

- [ ] **gRPC Server (services/grpc_server.py).** Сервер для Gateway: SubmitCommand, GetRobotState, GetTaskStatus, StreamEvents (server-side streaming).

- [ ] **gRPC Clients (services/grpc_clients.py).** Клиенты к Triton, vLLM, SmolVLA. Timeout 10s, retry 3x с exponential backoff, circuit breaker.

---

## Этап 8 — Тесты

- [ ] **conftest.py.** Фикстуры: async PostgreSQL (testcontainers или SQLite in-memory), mock Redis, mock MQTT, mock gRPC services, sample SwarmState.

- [ ] **Unit: state + reducers.** Тесты SwarmState: создание, обновление через reducers, валидация типов.

- [ ] **Unit: agents.** Тесты каждого агента: правильные instructions, tools привязаны, guardrails работают, handoffs корректны.

- [ ] **Unit: guardrails.** Тесты input/output/safety guardrails: pass, block, tripwire сценарии.

- [ ] **Unit: managers.** TaskManager CRUD, ResourceManager назначение (mock robot states), CoordinationManager распределение зон.

- [ ] **Integration: LangGraph.** Тест полного графа: intake → planning → assignment → execution → evaluation → reporting с mock AI-сервисами.

- [ ] **Integration: Celery tasks.** Тест задач с реальным RabbitMQ (testcontainers) и Redis backend.

- [ ] **Integration: MQTT.** Тест publish/subscribe команд с реальным EMQX (testcontainers).
