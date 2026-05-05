# GPTHub — переменные окружения

Источник шаблона: `docker/.env.example`.

> Рекомендуемый процесс: копируйте `.env.example` в `.env.dev` / `.env.prod` и меняйте только значения.

## Общие правила

- Формат: `SECTION__NAME=value`
- `docker/run.sh` ожидает файлы:
  - `docker/.env.dev`
  - `docker/.env.prod`
- Не храните production-секреты в git.

---

## 1) Docker / release

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `APP_TAG` | Нет | `latest` | Тег релиза образов |
| `APP_DOCKERHUB_REPO` | Нет | `your-repo` | Репозиторий образов |
| `MODE` | Нет | `dev` | Режим по умолчанию |

## 2) Сервис и frontend URL

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `SERVICE__LOGGING_LEVEL` | Нет | `DEBUG` | Уровень логов backend |
| `SERVICE__SERVER_PORT` | Нет | `8000` | Порт backend внутри контейнера |
| `SERVICE__NAME` | Нет | `service-api` | Имя сервиса |
| `SERVICE__APP_DOMAIN` | Да (prod) | `gpthub.example.com` | Домен для внешнего доступа |
| `SERVICE__ADMIN_USER_IDS` | Нет | `uuid1,uuid2` | Список admin user id |
| `SERVICE__NGINX_PORT` | Нет | `80` | Порт nginx |
| `SERVICE__REACT_APP_API_BASE_URL` | Да | `http://localhost:8000` | Базовый URL API для frontend |
| `SERVICE__REACT_APP_WS_BASE_URL` | Да | `ws://localhost:8000` | Базовый URL WebSocket |
| `SERVICE__REACT_APP_ENABLE_ADMIN_UI` | Нет | `true` | Флаг админ-элементов UI |

## 3) Auth

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `AUTH__SECRET` | Да | `long-random-string` | JWT secret |
| `AUTH__ALGORITHM` | Нет | `HS256` | Алгоритм подписи JWT |
| `AUTH__JWT_EXP_HOURS` | Нет | `24` | Время жизни JWT в часах |
| `AUTH__AUTH_MODE` | Нет | `prod` / `dev` | Режим auth-политики для каналов WS |
| `AUTH__WS_AUTH_ALLOWLIST_PROD` | Нет | `["jwt_cookie"]` | Явный allowlist каналов auth в production |
| `AUTH__WS_AUTH_ALLOWLIST_DEV` | Нет | `["jwt_cookie","query_token","authorization_bearer","session_cookie","anon_token"]` | Явный allowlist каналов auth в development |
| `AUTH__ENABLE_LEGACY_WS_TOKEN_AUTH` | Нет | `false` | Feature-flag legacy session token каналов в WS |
| `AUTH__ENABLE_DEV_TEST_TOKEN` | Нет | `false` | Разрешить dev `test-token` сценарий |
| `AUTH__ENFORCE_PROD_RUNTIME_AUTH_GUARD` | Нет | `true` | Runtime guard на запрет downgrade/dev-token в production |
| `AUTH__DEV_MODE` | Нет | `True` | Старый флаг dev режима (для обратной совместимости) |

## 4) CORS

| Переменная | Обязательна | Пример |
|---|---:|---|
| `CORS__ALLOW_ORIGINS` | Да | `["https://your-domain.example.com","http://localhost:3000"]` |

## 5) Storage

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `STORAGE__ROOT` | Нет | `/var/lib/app/storage` | Корень локального storage |
| `STORAGE__BACKEND` | Да | `local` / `minio` | Выбор backend хранения |

## 6) Agents / LLM

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `AGENTS__LLM_PROVIDER` | Да | `mws` / `openai` | Текущий провайдер по умолчанию |
| `AGENTS__MWS_API_KEY` | Условно | `***` | API key MWS |
| `AGENTS__MWS_BASE_URL` | Условно | `https://api.gpt.mws.ru/v1` | Endpoint MWS |
| `AGENTS__MWS_TIMEOUT_SEC` | Нет | `240` | Таймаут запросов к MWS |
| `AGENTS__MWS_MODELS_CACHE_TTL_SEC` | Нет | `180` | TTL списка моделей |
| `AGENTS__OPENAI_API_KEY` | Условно | `***` | API key OpenAI |
| `AGENTS__OPENAI_BASE_URL` | Условно | `https://api.openai.com/v1` | Endpoint OpenAI |
| `AGENTS__CHAT_HISTORY_MESSAGES_LIMIT` | Нет | `10` | Глубина истории в контексте |
| `AGENTS__MAX_CONTEXT_CHARS` | Нет | `150000` | Лимит символов контекста |
| `AGENTS__MAX_TURNS` | Нет | `15` | Лимит итераций агента |

### Долгосрочная память (Mem0)

| Переменная | Обязательна | Пример | Назначение |
|---|---:|---|---|
| `AGENTS__MEM0_API_KEY` | Условно | `***` | Ключ mem0/mem0ai |
| `AGENTS__MEM0_APP_ID` | Нет | `gpthub` | Идентификатор приложения в mem0 |

Также поддерживаются fallback-имена: `MEM0_API_KEY`, `MEM0_APP_ID`.

## 7) Proxy (опционально)

| Переменная | Обязательна | Назначение |
|---|---:|---|
| `AGENTS__PROXY_HOST` | Нет | Хост прокси |
| `AGENTS__PROXY_PORT` | Нет | Порт прокси |
| `AGENTS__PROXY_USER` | Нет | Логин прокси |
| `AGENTS__PROXY_PASS` | Нет | Пароль прокси |

## 8) PostgreSQL

| Переменная | Обязательна | Пример |
|---|---:|---|
| `PG__USER` | Да | `postgres` |
| `PG__PASSWORD` | Да | `***` |
| `PG__HOST` | Да | `postgres` |
| `PG__PORT` | Нет | `5432` |
| `PG__DB` | Да | `main` |

## 9) MinIO (если `STORAGE__BACKEND=minio`)

| Переменная | Обязательна | Пример |
|---|---:|---|
| `MINIO__ENDPOINT` | Да | `minio:9000` |
| `MINIO__ACCESS_KEY` | Да | `minioadmin` |
| `MINIO__SECRET_KEY` | Да | `***` |
| `MINIO__BUCKET` | Да | `gpthub` |
| `MINIO__REGION` | Нет | `us-east-1` |
| `MINIO__SECURE` | Нет | `false` |
| `MINIO__PUBLIC_ENDPOINT` | Да | `http://localhost:9000` |
| `MINIO__RETRY_ATTEMPTS` | Нет | `3` |
| `MINIO__RETRY_BACKOFF` | Нет | `0.5` |
| `MINIO__PRESIGN_EXPIRY` | Нет | `3600` |

## 10) Redis

| Переменная | Обязательна | Пример |
|---|---:|---|
| `REDIS__ENABLED` | Нет | `true` |
| `REDIS__HOST` | Да | `redis` |
| `REDIS__PORT` | Нет | `6379` |
| `REDIS__DB` | Нет | `0` |
| `REDIS__PASSWORD` | Да | `***` |
| `REDIS__SESSION_PREFIX` | Нет | `session` |
| `REDIS__SESSION_TTL_SECONDS` | Нет | `3600` |
| `REDIS__CACHE_PREFIX` | Нет | `cache` |
| `REDIS__CACHE_DEFAULT_TTL_SECONDS` | Нет | `300` |
| `REDIS__PROFILE_CACHE_TTL_SECONDS` | Нет | `900` |

## 11) Celery

| Переменная | Обязательна | Пример |
|---|---:|---|
| `CELERY__BROKER_URL` | Да | `redis://:password@redis:6379/0` |
| `CELERY__RESULT_BACKEND` | Да | `redis://:password@redis:6379/1` |
| `CELERY__QUEUES` | Нет | `agents,maintenance` |

---

## Минимальный набор для локального старта

Если хотите просто поднять dev-стек, проверьте хотя бы эти ключи:

- `AUTH__SECRET`
- `PG__USER`, `PG__PASSWORD`, `PG__DB`
- `REDIS__PASSWORD`
- `SERVICE__REACT_APP_API_BASE_URL`
- `SERVICE__REACT_APP_WS_BASE_URL`
- один из LLM API key (`AGENTS__MWS_API_KEY` или `AGENTS__OPENAI_API_KEY`)

## Безопасность

- Используйте разные секреты для `.env.dev` и `.env.prod`.
- Не публикуйте реальные ключи в репозитории, issue и чатах.
- Перед презентацией убедитесь, что в логах не выводятся чувствительные значения.