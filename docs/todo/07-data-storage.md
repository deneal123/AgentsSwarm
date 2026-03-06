# TODO: Data Storage

Инфраструктура хранения данных: PostgreSQL, InfluxDB, Neo4j, Redis, MinIO. Схемы, миграции, инициализация, shared-библиотека клиентов.

---

## Этап 1 — PostgreSQL

- [ ] **init.sql — начальная инициализация.** Создание БД `agentsswarm`, пользователя, расширений: uuid-ossp (генерация UUID), pgcrypto (хеширование паролей), pg_trgm (fuzzy search).

- [ ] **Alembic — начальная миграция.** Создание всех таблиц: users, robots, tasks, incidents, audit_logs, zones, model_versions, configurations. Индексы, constraints, FK.

- [ ] **Enum-типы.** PostgreSQL ENUM: robot_status (IDLE, ACTIVE, CHARGING, MAINTENANCE, ERROR, OFFLINE), task_status (PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED), incident_severity (LOW, MEDIUM, HIGH, CRITICAL), user_role (OPERATOR, SUPERVISOR, ADMIN).

- [ ] **JSONB индексы.** GIN-индексы на JSONB-поля: robots.config, tasks.params, tasks.result, audit_logs.details. Для эффективного поиска по вложенным полям.

- [ ] **Partial indexes.** Индексы на активные сущности: `WHERE status IN ('PENDING','ASSIGNED','IN_PROGRESS')` для tasks, `WHERE status != 'OFFLINE'` для robots.

- [ ] **Materialized views.** Предвычисленные агрегаты: robot_status_summary (count по статусам), task_stats_daily (средняя длительность, success rate за день), active_incidents (незакрытые инциденты).

- [ ] **Seed data.** Скрипт seed-data.sh: тестовые пользователи (admin, operator), зоны (warehouse, inspection_area), роботы (5 шт. разных типов), задачи (10 шт. в разных статусах).

---

## Этап 2 — InfluxDB

- [ ] **init.sh — создание ресурсов.** Организация `agentsswarm`, бакеты: `telemetry` (retention 30 дней), `metrics` (retention 90 дней), `events` (retention 365 дней).

- [ ] **API-токены.** Создание read/write токенов для сервисов: orchestrator (read+write telemetry), gateway (read telemetry), monitoring (read all). Минимальные привилегии.

- [ ] **Схема телеметрии.** Measurement `robot_telemetry`: tags (robot_id, zone_id, robot_model), fields (position_x, position_y, position_z, velocity, battery, cpu_temp, gpu_temp, signal_strength). Timestamp — nano precision.

- [ ] **Схема метрик сервисов.** Measurement `service_metrics`: tags (service_name, instance_id), fields (request_count, error_count, latency_p50, latency_p99, memory_mb, cpu_percent).

- [ ] **Схема событий.** Measurement `robot_events`: tags (robot_id, event_type, severity), fields (description, details_json). Для долгосрочного хранения событий.

- [ ] **Downsampling tasks.** InfluxDB tasks для агрегации: raw telemetry (каждую секунду) → 1-минутные средние → 1-часовые средние. Экономия хранилища.

---

## Этап 3 — Neo4j

- [ ] **init.cypher — constraints.** Uniqueness constraints: Robot(id), Zone(id), Object(id), User(id). Existence constraints для обязательных полей.

- [ ] **init.cypher — indexes.** Composite indexes: Robot(status, zone_id), Object(class_name), Zone(type). Full-text index на Object(description) для текстового поиска.

- [ ] **Граф-модель: ноды.** Типы нод: Robot (id, model, status, capabilities), Zone (id, name, type, boundaries), Object (id, class_name, position, last_seen), User (id, name, role).

- [ ] **Граф-модель: связи.** Типы связей: Robot-[:LOCATED_IN]->Zone, Robot-[:ASSIGNED_TO]->Task, Robot-[:DETECTED]->Object (timestamp, confidence), Zone-[:ADJACENT_TO]->Zone, Robot-[:NEAR]->Robot (distance).

- [ ] **Пространственные запросы.** Cypher-запросы для пространственного анализа: роботы в радиусе N от точки, кратчайший путь между зонами, объекты в зоне.

- [ ] **Seed data.** Начальный граф: зоны (связи adjacency), роботы (размещение в зонах), тестовые объекты.

---

## Этап 4 — Redis

- [ ] **redis.conf — конфигурация.** Maxmemory 2GB (dev), eviction policy allkeys-lru, appendonly yes (AOF), save rules для RDB snapshots.

- [ ] **Модули.** Включение: RedisJSON, RediSearch, RedisTimeSeries. Проверка загрузки через MODULE LIST.

- [ ] **Feature Store схема.** Hash-ключи: `robot:{id}:state` (status, battery, position_x, position_y, zone_id, last_seen), `robot:{id}:detections` (JSON массив последних детекций), `features:{id}:latest` (агрегированные ML-признаки).

- [ ] **TimeSeries ключи.** Создание TS ключей при регистрации робота: `ts:robot:{id}:battery`, `ts:robot:{id}:velocity`, `ts:robot:{id}:temperature`. Labels: robot_id, robot_model, zone_id. Retention: 3600000ms (1 час).

- [ ] **Search индексы.** RediSearch index на Robot hashes: TextField (status), NumericField (battery), TagField (zone_id, model). Для быстрого поиска: роботы с батареей > 50% в зоне X.

- [ ] **Streams.** Создание streams: `events:robot` (события роботов), `events:task` (события задач), `events:system` (системные). Consumer groups: orchestrator, monitoring, logging.

- [ ] **Pub/Sub каналы.** Документация каналов: `telemetry:{robot_id}`, `notifications:{user_id}`, `chat.responses:{user_id}`, `config.updates`.

---

## Этап 5 — MinIO

- [ ] **init.sh — создание бакетов.** Бакеты: models, datasets, rosbags, videos, maps, snapshots, audit-logs, backups. С корректными регионами.

- [ ] **Versioning.** Включение versioning на бакетах: models, datasets, maps. Для отслеживания версий моделей и датасетов.

- [ ] **Lifecycle rules.** Правила: rosbags — 30 дней на SSD → удаление, videos — 7 дней → удаление, snapshots — 30 дней → удаление, audit-logs — 365 дней.

- [ ] **Object Lock.** COMPLIANCE lock на бакете audit-logs: 365 дней. Объекты не могут быть удалены или перезаписаны.

- [ ] **Bucket policies.** IAM-политики: orchestrator — read/write models + datasets, triton — read models, vllm — read models + lora_adapters, robot_edge — read models + write rosbags.

- [ ] **Event notifications.** Notification на бакете models: s3:ObjectCreated:Put → RabbitMQ exchange `model.events` для автоматической перезагрузки моделей на Triton/vLLM.

- [ ] **Seed data.** Загрузка тестовых моделей (small ONNX файл), тестовых изображений, sample rosbag.

---

## Этап 6 — Shared Python library (agentsswarm-db)

- [ ] **Создать shared package agentsswarm-db.** Общая Python-библиотека для работы с хранилищами. Устанавливается как зависимость в каждый микросервис. Публикуется в private PyPI или устанавливается через git+ssh.

- [ ] **PostgreSQL client.** Async engine factory, session factory, base model, типичные queries (get_robot, list_tasks, create_audit_log). Настроенный connection pool.

- [ ] **InfluxDB client.** Wrapper над influxdb3-python: write_telemetry(robot_id, data), query_telemetry(robot_id, from, to), write_metric(service, data).

- [ ] **Neo4j client.** Wrapper над neo4j driver: update_robot_location(robot_id, zone_id), find_nearby_robots(position, radius), get_zone_graph().

- [ ] **Redis client.** Wrapper над redis.asyncio: update_feature_store(robot_id, features), get_robot_state(robot_id), publish_event(channel, data), ts_add(key, value).

- [ ] **MinIO client.** Wrapper над minio-py: upload_model(name, version, path), download_model(name, version), get_presigned_url(bucket, key), list_model_versions(name).

---

## Этап 7 — Backup и DR

- [ ] **PostgreSQL backup.** CronJob: pg_dump → gzip → upload в MinIO бакет `backups/postgres/YYYY-MM-DD.sql.gz`. Retention 30 дней.

- [ ] **InfluxDB backup.** CronJob: influxd backup → upload в MinIO `backups/influxdb/`. Retention 14 дней.

- [ ] **Neo4j backup.** CronJob: neo4j-admin dump → upload в MinIO `backups/neo4j/`. Retention 14 дней.

- [ ] **Redis backup.** RDB snapshot copy → MinIO `backups/redis/`. Retention 7 дней (Redis данные восстанавливаемы из primary sources).

- [ ] **Restore скрипты.** restore-postgres.sh, restore-influxdb.sh, restore-neo4j.sh: загрузка из MinIO, восстановление, проверка целостности.

- [ ] **DR тестирование.** Quarterly тест: полное восстановление из бэкапов на изолированной среде, проверка целостности данных.

---

## Этап 8 — Тесты

- [ ] **PostgreSQL.** Тесты миграций: upgrade + downgrade. Тесты seed data. Тесты materialized views refresh.

- [ ] **InfluxDB.** Тесты write + query telemetry. Тесты downsampling tasks. Тесты retention policy (TTL).

- [ ] **Neo4j.** Тесты CRUD нод и связей. Тесты пространственных запросов. Тесты constraints (duplicate rejection).

- [ ] **Redis.** Тесты Feature Store CRUD. Тесты TimeSeries add + range. Тесты Streams xadd + xreadgroup + xack. Тесты Search index + query.

- [ ] **MinIO.** Тесты bucket operations. Тесты object put/get/delete. Тесты presigned URLs. Тесты lifecycle rules (mock time advance).

- [ ] **Shared library.** Тесты каждого клиента с testcontainers (реальные экземпляры БД в Docker).
