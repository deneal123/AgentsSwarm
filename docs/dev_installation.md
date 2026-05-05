# GPTHub — установка и запуск (dev/prod)

Документ для разработчиков: как поднять проект локально, проверить работоспособность и устранить типовые проблемы.

## 1) Требования

- Linux/macOS (Windows через WSL2)
- Docker Engine + Docker Compose v2
- `make` (опционально, можно запускать скрипты напрямую)

Проверка:

```bash
docker --version
docker compose version
make --version
```

## 2) Клонирование

```bash
git clone <repo-url>
cd GPTHub
```

## 3) Подготовка переменных окружения

Файлы окружения ожидаются в `docker/`:

```bash
cd docker
cp .env.example .env.dev
cp .env.example .env.prod
```

Далее заполните обязательные значения в `.env.dev` / `.env.prod`:

- `PG__USER`, `PG__PASSWORD`, `PG__DB`
- `REDIS__PASSWORD`
- `AUTH__SECRET`
- минимум один LLM-провайдер:
  - `AGENTS__MWS_API_KEY` (+ `AGENTS__MWS_BASE_URL`), или
  - `AGENTS__OPENAI_API_KEY` (+ `AGENTS__OPENAI_BASE_URL`)

Подробнее: [env_variables.md](./env_variables.md)

## 4) Запуск в dev-режиме

### Вариант A: через Makefile

```bash
cd /path/to/GPTHub
make build MODE=dev
make run MODE=dev
```

### Вариант B: напрямую через скрипты

```bash
cd /path/to/GPTHub/docker
./build.sh --dev
./run.sh --dev
```

## 5) Проверка после старта

```bash
cd /path/to/GPTHub/docker
./run.sh --status
```

Ожидаемые адреса (dev):

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001`

## 6) Полезные команды

```bash
cd /path/to/GPTHub/docker
./run.sh --logs
./run.sh --logs backend
./run.sh --logs frontend
./run.sh --restart
./run.sh --stop
```

## 7) Запуск production-стека

```bash
cd /path/to/GPTHub/docker
./build.sh --prod
./run.sh --prod
```

Ожидаемые внешние endpoints:

- `http://<APP_DOMAIN>`
- `http://<APP_DOMAIN>/api`
- `https://<APP_DOMAIN>` (если есть валидные TLS-файлы)

## 8) Smoke-check для презентации

После `--prod` выполните:

```bash
cd /path/to/GPTHub/docker
./run.sh --status
./run.sh --logs nginx
```

И проверьте руками:

1. Открывается главная страница.
2. Создаётся чат и приходит потоковый ответ.
3. Работает загрузка файла в чат.
4. Включаются `Веб-поиск` и `Deep Research`.
5. Отдаются `/api/health` и `/api/chats/models`.

## 9) Troubleshooting

### Проблема: контейнеры не стартуют

- Проверьте обязательные env-переменные.
- Проверьте занятые порты (`3000`, `8000`, `5432`, `9001`, `80`, `443`).

### Проблема: фронт не собирается (`craco: not found`)

- Локальная сборка требует `npm install` в `frontend/`.
- Через Docker это уже выполняется на этапе build.

### Проблема: `502 Bad Gateway` в prod

- Смотрите `./run.sh --logs nginx` и `./run.sh --logs backend`.
- Убедитесь, что `backend` healthy и доступен внутри compose-сети.

### Проблема: нет фоновой обработки

- В проекте используются Celery workers (agents/maintenance) и beat.
- Проверьте, что Redis доступен и worker-контейнеры running/healthy.

## 10) Рекомендации для команды

- Держите `.env.*` вне git или без реальных секретов.
- Перед PR проверяйте `./run.sh --status` и smoke сценарий чата.
- Для новых участников начните с dev-режима и только затем переходите к prod-контуру.

## 11) Безопасный rollout изменений enum

1. Измените значения enum в `backend/service/models/key_value.py`.
2. Скопируйте шаблон `backend/alembic/templates/enum_change_template.py` в `backend/alembic/versions/<revision>.py`.
3. В `upgrade()` добавьте:
   - backfill для строк со старыми/пустыми значениями;
   - `ALTER TYPE ... ADD VALUE IF NOT EXISTS ...` для новых значений;
   - SQL-проверки, что данные соответствуют новому контракту.
4. В `downgrade()` добавьте:
   - проверку, что в таблицах нет значений, отсутствующих в старом enum;
   - пересоздание enum через временный type и обратное приведение колонок.
5. Перед PR запустите:

```bash
cd backend
pytest tests/test_enum_schema_contract.py
python scripts/check_enum_revision_guard.py HEAD~1 HEAD
```

6. Если в PR меняются enum-файлы и нет новой миграции в `backend/alembic/versions/`, CI завершится ошибкой.
