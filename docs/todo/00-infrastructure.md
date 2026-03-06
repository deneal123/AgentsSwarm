# TODO: Инфраструктура и DevOps

Общая инфраструктура проекта: корневой репозиторий, Docker, CI/CD, мониторинг, скрипты развёртывания.

---

## Этап 1 — Инициализация корневого репозитория

- [x] **Создать корневой репозиторий AgentsSwarm.** Мета-репозиторий для docker-compose, инфраструктурных скриптов, документации и git submodules на все микросервисы.

- [x] **Создать .gitignore.** Исключить .env, __pycache__, node_modules, .vscode, *.pyc, volumes данных.

- [x] **Создать .env.example.** Шаблон с переменными окружения всех сервисов: URL-ы БД, порты, секреты JWT, адреса брокеров, GPU-конфигурация.

- [x] **Создать Makefile.** Цели: `up`, `down`, `build`, `logs`, `ps`, `clean`, `test`, `lint`, `migrate`, `seed` — обёртки над docker-compose и скриптами.

- [x] **Создать build.sh.** Скрипт сборки всех Docker-образов с тегированием по git-sha и semver. Поддержка `--service` для выборочной сборки.

- [x] **Создать run.sh.** Скрипт запуска всей системы с проверкой зависимостей (Docker, docker-compose, GPU drivers). Параметры: `--dev`, `--prod`, `--gpu`, `--no-gpu`.

---

## Этап 2 — Docker Compose (dev-среда)

- [x] **docker-compose.dev.yml — инфраструктурные сервисы.** PostgreSQL, InfluxDB, Neo4j, Redis Stack, MinIO — каждый с named volumes, healthcheck, фиксированными портами.

- [x] **docker-compose.dev.yml — брокеры сообщений.** EMQX (порты 1883, 8083, 18083) и RabbitMQ (порты 5672, 15672) с management UI, конфигурациями через volume mount.

- [x] **docker-compose.dev.yml — application-сервисы.** GatewayService, Orchestrator, Celery Worker, Communication Bridge — зависимости (depends_on) на БД и брокеры с condition: service_healthy.

- [x] **docker-compose.dev.yml — AI-сервисы (опционально).** Triton, vLLM, SmolVLA — профиль `gpu`, запуск только при наличии `nvidia-container-toolkit`. Runtime: `nvidia`.

- [x] **docker-compose.dev.yml — Frontend.** React dev server с hot-reload, volume mount src/, проксирование API через Vite proxy.

- [x] **docker-compose.dev.yml — мониторинг (профиль monitoring).** Prometheus, Grafana, Jaeger — запуск через `--profile monitoring`.

- [x] **docker-compose.yml — production-конфигурация.** Без volume mount для кода (только образы), ресурсные лимиты, restart: always, логирование в json-file с ротацией.

---

## Этап 3 — Инициализация БД

- [x] **PostgreSQL init.sql.** Создание базы, пользователя, расширений (uuid-ossp, pgcrypto). Начальная схема создаётся через Alembic из Orchestrator.

- [x] **InfluxDB init.sh.** Создание организации, бакетов (telemetry, metrics, events), API-токенов для сервисов (read/write раздельно).

- [x] **Neo4j init.cypher.** Constraints уникальности (Robot.id, Zone.id), индексы для частых запросов, установка APOC плагина.

- [x] **Redis modules.conf.** Конфигурация Redis Stack: RedisJSON, RediSearch, RedisTimeSeries — все модули включены, persistence AOF + RDB.

- [x] **MinIO init.sh.** Создание бакетов (models, datasets, rosbags, videos, maps, snapshots, audit-logs), policies, versioning, lifecycle rules.

- [x] **Скрипт seed-data.sh.** Тестовые данные для разработки: пользователи, роботы, зоны, задачи, телеметрия (timerange за последний час).

---

## Этап 4 — Protobuf контракты

- [x] **Установить buf для управления Protobuf.** Конфигурация buf.yaml, buf.gen.yaml для генерации Python и TypeScript клиентов.

- [x] **common/v1/types.proto.** Общие типы: Timestamp, Position, BoundingBox, RobotStatus enum, TaskStatus enum, Severity enum.

- [x] **common/v1/telemetry.proto.** Телеметрия робота: position, battery, velocity, sensor readings, timestamp.

- [x] **orchestrator/v1/orchestrator.proto.** gRPC сервис: SubmitCommand, GetTaskStatus, GetRobotState, StreamEvents.

- [x] **inference/v1/triton.proto.** Обёртка над Triton: DetectObjects, TrackObjects — с метаданными AgentsSwarm.

- [x] **inference/v1/smolvla.proto.** gRPC сервис SmolVLA: PredictAction (image + instruction → action chunk).

---

## Этап 5 — CI/CD (GitHub Actions)

- [x] **Lint & Type Check workflow.** `.github/workflows/lint.yml` — матрица по 7 Python-сервисам (ruff check, ruff format --check, mypy, bandit), frontend (eslint, tsc --noEmit), proto (buf lint + buf breaking на PR). Кэш Poetry virtualenv, skip при отсутствии pyproject.toml. Job `lint-summary` агрегирует результаты.

---

## Этап 6 — Скрипты и утилиты

- [x] **health-check.sh.** Проверка всех сервисов: HTTP health endpoints, TCP-подключения к БД и брокерам. Вывод статуса в таблицу.

- [x] **backup.sh.** `mktemp -d` + `trap EXIT` для temp-файлов. pg_dump `-Fc` → local file → mc cp (исправлен broken pipe). influx backup → docker cp → tar.gz → mc cp. Neo4j через APOC `apoc.export.json.all` (Community Edition workaround). Retention: `mc find --older-than Nh`. `--dry-run`, `--postgres/--influxdb/--neo4j`, итоговая таблица.

- [x] **restore.sh.** `--list` (показать доступные даты из MinIO), `--date`/`--latest` для выбора бэкапа, `--postgres/--influxdb/--neo4j/--all`. pg_restore с предварительным drop/create DB. InfluxDB: `influx restore --full`. Neo4j: `MATCH (n) DETACH DELETE n` + `apoc.import.json`. Запрос подтверждения (обход через `--yes`).

- [x] **init-db.sh.** Комплексная инициализация всех БД: вызов init-скриптов PostgreSQL, InfluxDB, Neo4j, Redis, MinIO.
