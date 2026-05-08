# GPTHub Backend API Documentation

**Последнее обновление:** 2026-05-08  
**Статус:** Актуализировано по текущим роутерам backend

Документ описывает актуальные REST и WebSocket контракты из:

- `backend/service/presentation/routers/*`
- `backend/service/services/chat/presentation/routers/*`

---

## 🚀 Базовая информация

### Базовый URL

```text
http://localhost:8000
```

### OpenAPI / Swagger

- Swagger UI: `GET /api/docs`
- OpenAPI JSON: `GET /api/openapi.json`
- ReDoc: `GET /api/redoc`

### Health check

```http
GET /api/health
```

Ответ:

```json
{"status": "ok"}
```

---

## 🧪 Контрактная валидация

- OpenAPI генерируется из текущего приложения FastAPI: `python backend/scripts/export_openapi.py --output backend/artifacts/openapi.json`.
- В CI публикуется артефакт `openapi-schema` с актуальным `openapi.json`.
- Критичные endpoint-контракты сверяются с эталонным snapshot: `backend/tests/snapshots/critical_endpoint_openapi.json`.
- DTO-контракты ответов сверяются со snapshot: `backend/tests/snapshots/critical_response_schemas.json`.
- Если контракт изменился, нужно обновить snapshots и документацию.

---

## 🔐 Аутентификация

### Как устроено сейчас

Для защищённых REST endpoints используется cookie:

- `auth_token` (JWT, HttpOnly)

Проверка делается единым validator'ом JWT/session с централизованной телеметрией отказов (`auth_validation_failures_total`).

### Security policy (prod/dev)

- Политика каналов WS auth конфигурируется через `AUTH__AUTH_MODE`.
- Для каждого режима используется явный allowlist:
  - `AUTH__WS_AUTH_ALLOWLIST_PROD`
  - `AUTH__WS_AUTH_ALLOWLIST_DEV`
- Legacy token auth для WS контролируется feature-flag `AUTH__ENABLE_LEGACY_WS_TOKEN_AUTH`.
- Dev `test-token` контролируется отдельным флагом `AUTH__ENABLE_DEV_TEST_TOKEN`.
- В production runtime guard (`AUTH__ENFORCE_PROD_RUNTIME_AUTH_GUARD=true`) блокирует downgrade/dev-token сценарии.

### Важно

- Эндпоинты `Profile`, `Memory`, `Files`, `Jobs` требуют `auth_token`.
- Чат REST (`/api/chats/*`) в текущей версии **не требует** `check_auth`.
- Для WS в production рекомендуется allowlist только `jwt_cookie`.
- Ротация JWT выполняется через обычный flow login/re-login; после ротации старые сессионные токены должны быть инвалидированы.
- Cookie policy для `auth_token`: `HttpOnly`, `Secure` (в prod), `SameSite=Strict` (в prod).

---

## 👤 Auth API

Префикс: `/api/auth/v1`

### POST `/register`

Регистрация пользователя.

Request:

```json
{
  "email": "user@example.com",
  "password": "strong-password",
  "fingerprint": "optional-device-fingerprint"
}
```

Response:

```json
{
  "email": "user@example.com",
  "user_id": "uuid"
}
```

### POST `/login`

Логин, возвращает JWT и устанавливает cookie `auth_token`.

Request:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

Response body:

```json
{
  "jwt": "<token>"
}
```

---

## 💬 Chat REST API

Префикс: `/api/chats`

### GET `/models`

Список доступных LLM моделей для чата (фильтруются embedding/rerank модели).

Response:

```json
{
  "models": ["model-id-1", "model-id-2"]
}
```

### POST `/`

Создать новый чат-тред.

Request:

```json
{
  "user_id": 123,
  "title": "Новый чат"
}
```

Response:

```json
{
  "thread_id": "uuid-or-id",
  "title": "Новый чат",
  "created_at": "2026-04-15T00:00:00Z"
}
```

### GET `/`

Список тредов.

Query params:

- `user_id` (optional)
- `page` (default `1`)
- `per_page` (default `50`)

### GET `/{thread_id}`

Сообщения конкретного треда.

Query params:

- `page` (default `1`)
- `per_page` (default `50`)

### DELETE `/{thread_id}`

Удалить тред.

Response: `204 No Content`

### POST `/{thread_id}/message`

Отправить сообщение агенту (REST path).

Request schema:

```json
{
  "text": "Обязательный текст",
  "user_id": "optional-int-or-string",
  "model": "optional-model-id",
  "input_type": "text|image|audio|video",
  "web_search": false,
  "deep_research": false,
  "route_override": "general|web_search|deep_research|image_gen|pptx_gen",
  "file_context": "optional extracted text",
  "file_ids": ["optional-temp-file-id"]
}
```

Response schema:

```json
{
  "reply": "string",
  "thread_id": "optional",
  "metadata": {}
}
```

### POST `/upload`

Загрузка файла в чат с попыткой извлечения контента.

`multipart/form-data`:

- `file` (required)
- `thread_id` (optional)
- `user_id` (optional)

Поддерживаемые форматы:

- text: `.txt`, `.md`, `.csv`, `.json`
- docs: `.pdf`, `.docx`
- image: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` (VLM описание)
- audio: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`, `.webm` (ASR `whisper-1`)

Response (пример):

```json
{
  "filename": "spec.pdf",
  "file_type": "pdf",
  "size": 12345,
  "extracted_text": "...",
  "thread_id": "...",
  "file_id": "optional",
  "file_url": "optional",
  "file_key": "optional",
  "temp_file": true
}
```

### POST `/web-search`

Прокси для web search tool.

Params:

- `q` (required)
- `num_results` (default 5, max 10)

### POST `/parse-url`

Парсинг URL и извлечение контента.

Params:

- `url` (required)

### POST `/generate-pptx`

Генерация PPTX по теме.

Params:

- `topic` (required)

Response: бинарный `application/vnd.openxmlformats-officedocument.presentationml.presentation`

### GET `/files/download`

Скачивание сгенерированного файла по `file_key`.

Query params:

- `file_key` (required)
- `filename` (optional)

Поведение:

- для object storage может вернуть `307 Redirect` на presigned URL,
- для local storage возвращает binary response.

---

## ⚙️ Jobs REST API

Префикс: `/api/jobs/v1` (требует `auth_token`)

### POST `/start`

Запуск фоновой задачи.

Request:

```json
{
  "file_id": "uuid",
  "target_column": "optional",
  "type": "CHAT|CALENDAR|..."
}
```

### GET `/result/{job_id}`

Получить статус/результат job.

### GET `/task/{task_id}/status`

Статус Celery task.

### POST `/task/{task_id}/cancel`

Отмена Celery task.

---

## 📁 Files API

Префикс: `/api/service/files/v1` (требует `auth_token`)

### GET `/modes`

Доступные `ServiceType`.

### GET `/fetch/{mode}`

Список файлов пользователя по режиму.

### POST `/upload/{mode}`

Загрузка файла (валидация расширений и размера).

### DELETE `/delete/{file_id}`

Удаление файла.

### POST `/presign/{mode}`

Получить presigned upload URL.

Request:

```json
{
  "filename": "report.csv",
  "expiry_sec": 3600
}
```

### POST `/{file_id}/callback`

Финализация direct-upload после загрузки в storage.

Request:

```json
{
  "file_key": "storage/key",
  "mode": "CHAT"
}
```

### GET `/{file_id}`

Метаданные файла + (если доступно) `download_url`.

---

## 🙍 Profile API

Префикс: `/api/profile` (требует `auth_token`)

### GET `/me`

Профиль текущего пользователя.

### PATCH `/me`

Обновление профиля.

Request (частичный):

```json
{
  "first_name": "Иван",
  "company": "InCellCorp",
  "timezone": "Europe/Moscow",
  "avatar_url": "https://..."
}
```

### DELETE `/me/chat-history`

Удалить историю чатов пользователя.

---

## 🧠 Memory API

Префикс: `/api/memory` (требует `auth_token`, доступ только к своему `user_id`)

### GET `/{user_id}`

Вернуть список фактов + контекст памяти.

### GET `/{user_id}/search?q=...`

Поиск по фактам памяти.

### POST `/{user_id}/facts`

Добавить факт.

Request:

```json
{
  "user_id": "optional-same-user-id",
  "fact_type": "general",
  "fact_key": "preferred_language",
  "fact_value": "ru"
}
```

### DELETE `/{user_id}/facts/{fact_id}`

Удалить факт.

---

## 🔌 WebSocket API

## Chat WS

Endpoint: `WS /api/chats/{thread_id}/ws`

### Incoming (client -> server)

```json
{
  "type": "message",
  "id": "msg-id",
  "text": "Текст",
  "user_id": "optional",
  "model": "optional-model",
  "route_override": "optional",
  "input_type": "text|image|audio|video",
  "web_search": false,
  "deep_research": false,
  "file_context": "optional",
  "file_ids": ["optional"]
}
```

### Outgoing (server -> client, ключевые типы)

- `job_created`
- `processing`
- `routing_start` / `routing_complete`
- `tool_call_start` / `tool_call_complete` / `tool_call_error`
- `stream_chunk`
- `stream_complete`
- `status_update`
- `structured_output`
- `agent_reply`
- `agent_start` / `agent_complete`
- `error`
- `heartbeat`

## Jobs WS

Endpoint: `WS /api/jobs/v1/{job_id}/ws`

Auth: согласно allowlist-политике (`AUTH__WS_AUTH_ALLOWLIST_*`) и feature-flags legacy/dev-token.

Поведение:

- читает `job:{job_id}:stream`,
- поддерживает replay (`last_id`) и claim pending,
- отправляет heartbeat при отсутствии новых данных.

---

## 🧪 Debug API (только для отладки)

Префикс: `/api/debug`

- `GET /session/{token}` — посмотреть сессию по токену.
- `POST /emit` — вручную положить payload в `chat:{thread_id}:stream`.

> Не используйте debug endpoints в production-периметре без ограничений доступа.

---

## Примечания по совместимости

- Некоторые поля/подписи поддерживают legacy-path для обратной совместимости (например, в WS и ChatService fallback).
- Для интеграций ориентируйтесь на OpenAPI (`/api/openapi.json`) и этот документ как на human-readable карту API.# Backend API Documentation

**Последнее обновление**: 2025-12-28
**Статус**: Production Ready ✅

Полная документация всех REST API эндпоинтов и WebSocket соединений backend'а с описанием контрактов, параметров и примеров использования.

---

## 🚀 Быстрый старт

### Базовый URL
```
http://localhost:8000/api
```

### Аутентификация
Большинство эндпоинтов требуют аутентификации через:
- **Query параметр**: `?token=<session_token>`
- **Authorization header**: `Bearer <session_token>`
- **Cookie**: `session_token` или `session`

### Health Check
```http
GET /api/health
```
```json
{"status": "ok"}
```

---

## 💬 Chat API (Агенты)

### WebSocket: Chat Streaming
**Endpoint**: `WS /api/chats/{thread_id}/ws`

Потоковое взаимодействие с AI агентами (чат-ботами) в реальном времени.

#### Подключение
```javascript
const ws = new WebSocket('ws://localhost:8000/api/chats/my-thread/ws?token=session_token');
```

#### Входящие сообщения (Client → Server)

##### Chat Message
```typescript
interface ChatMessageIn {
  type: "message";
  id: string;        // Уникальный ID сообщения
  text: string;      // Текст сообщения (обязательно)
  user_id?: number;  // ID пользователя (опционально)
}
```

**Пример:**
```json
{
  "type": "message",
  "id": "msg-123",
  "text": "Создай календарь питания на 3 дня",
  "user_id": 123
}
```

#### Исходящие сообщения (Server → Client)

##### Job Created (первое сообщение)
```typescript
interface JobCreatedOut {
  type: "job_created";
  job_id: string;
  celery_task_id: string;
  message: string;
}
```

##### Agent Response Chunk
```typescript
interface AgentResponseOut {
  event: "agent_response";
  seq: number;
  data: string;
  metadata?: object;
}
```

На переходный релиз в `metadata` дублируются ключи `guardrails` и legacy `guardrials` для обратной совместимости клиентов.

##### Agent Complete
```typescript
interface AgentCompleteOut {
  event: "agent_complete";
  job_id: string;
  reply: string;
  file_url?: string;
  metadata?: object;
}
```

##### Error
```typescript
interface ErrorOut {
  event: "error";
  error: string;
}
```

#### Пример полного диалога

**Client → Server:**
```json
{
  "type": "message",
  "id": "calendar-001",
  "text": "Создай календарь питания для похудения на неделю"
}
```

**Server → Client (последовательно):**
```json
// 1. Job created
{
  "type": "job_created",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "celery-task-123",
  "message": "Processing your message..."
}

// 2. Agent processing (chunks)
{
  "event": "agent_response",
  "seq": 1,
  "data": "Анализирую ваш запрос..."
}

// 3. Final result
{
  "event": "agent_complete",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "reply": "Вот ваш персональный план питания на неделю...",
  "file_url": "http://localhost:9000/files/calendar_123.xlsx",
  "metadata": {
    "structured_output": {
      "calendar": [...]
    }
  }
}
```

### REST API: Chat Messages

#### POST Создать сообщение
**Endpoint**: `POST /api/chats/{thread_id}/message`

Отправка сообщения агенту через REST API (синхронный ответ).

**Request:**
```typescript
interface MessageRequest {
  text: string;      // Текст сообщения (обязательно, min 1 символ)
  user_id?: number;  // ID пользователя
}
```

**Response:**
```typescript
interface MessageResponse {
  reply: string;
  thread_id?: string;
  metadata?: object;
}
```

**Пример:**
```bash
curl -X POST "http://localhost:8000/api/chats/my-thread/message" \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Привет, создай рецепт салата",
    "user_id": 123
  }'
```

#### POST Создать тред
**Endpoint**: `POST /api/chats/`

Создание нового чат-треда.

**Request:**
```typescript
interface ThreadCreate {
  user_id?: number;
  title?: string;
}
```

**Response:**
```typescript
interface ThreadResponse {
  thread_id: string;
  title?: string;
  created_at?: string;
}
```

---

## ⚙️ Jobs API (Фоновые задачи)

### WebSocket: Job Streaming
**Endpoint**: `WS /api/jobs/v1/{job_id}/ws`

Отслеживание статуса фоновых задач в реальном времени.

#### Подключение
```javascript
const ws = new WebSocket('ws://localhost:8000/api/jobs/v1/550e8400-e29b-41d4-a716-446655440000/ws?token=session_token');
```

#### Исходящие сообщения (Server → Client)

##### Progress Update
```typescript
interface JobProgressOut {
  event: "progress";
  progress: number;  // 0-100
  timestamp?: string;
}
```

##### Data Chunk
```typescript
interface JobChunkOut {
  event: "chunk";
  seq: number;
  data: any;
}
```

##### Job Completed
```typescript
interface JobCompletedOut {
  event: "completed";
  calendar_id?: string;
  result?: object;
}
```

##### Job Error
```typescript
interface JobErrorOut {
  event: "error";
  error: string;
}
```

### REST API: Job Management

#### POST Запустить задачу
**Endpoint**: `POST /api/jobs/v1/start`

Запуск новой фоновой задачи (календарь, обработка файла и т.д.).

**Request:**
```typescript
interface StartJobRequest {
  file_id?: string;      // UUID файла для обработки
  dataset_id?: string;   // Legacy: ID датасета
  target_column?: string; // Целевая колонка для обучения
  type: ServiceType;     // Тип сервиса (CHAT, CALENDAR, etc.)
  mode?: ServiceMode;    // Режим сервиса
}
```

**Response:**
```typescript
interface JobResponse {
  job_id: string;           // UUID задачи
  status: ProcessingStatus; // NEW, PROCESSING, SUCCESS, FAILURE
  result_file_url?: string; // URL готового файла
  available_launches: number; // Остаток запусков
  wait_time_sec: number;    // Время ожидания
  celery_task_id?: string;  // ID Celery задачи
}
```

**Enums:**
```typescript
enum ServiceType {
  CHAT = "CHAT",
  CALENDAR = "CALENDAR",
  // ... другие типы
}

enum ServiceMode {
  CHAT = "CHAT",
  CALENDAR = "CALENDAR",
  // ... другие режимы
}

enum ProcessingStatus {
  NEW = "NEW",
  PROCESSING = "PROCESSING",
  SUCCESS = "SUCCESS",
  FAILURE = "FAILURE"
}
```

#### GET Получить результат задачи
**Endpoint**: `GET /api/jobs/v1/result/{job_id}`

Получение статуса и результата задачи.

**Response:** `JobResponse` (см. выше)

#### GET Статус Celery задачи
**Endpoint**: `GET /api/jobs/v1/task/{task_id}/status`

Получение статуса Celery задачи.

**Response:**
```typescript
interface TaskStatusResponse {
  task_id: string;
  state: string;      // PENDING, STARTED, SUCCESS, FAILURE
  progress?: number;  // 0-100
  status?: string;    // Человеко-читаемый статус
  result?: object;    // Результат если готово
  error?: string;     // Ошибка если провалено
}
```

---

## 📁 Files API (Файловое хранилище)

### GET Доступные режимы
**Endpoint**: `GET /api/files/v1/modes`

Получение списка доступных режимов загрузки файлов.

**Response:**
```json
["CALENDAR", "PHOTO", "DOCUMENT"]
```

### GET Список файлов пользователя
**Endpoint**: `GET /api/files/v1/fetch/{mode}`

Получение метаданных файлов пользователя по режиму.

**Response:**
```typescript
interface FileMetadata {
  file_id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  download_url: string;
}
```

### POST Загрузить файл
**Endpoint**: `POST /api/files/v1/upload/{mode}`

Прямая загрузка файла.

**Request:** Multipart form-data
- `file`: бинарный файл
- `metadata`: JSON строка с дополнительной информацией

**Response:**
```typescript
interface UploadResponse {
  file_id: string;
  filename: string;
  size_bytes: number;
  download_url: string;
}
```

### POST Создать presigned URL
**Endpoint**: `POST /api/files/v1/presign/{mode}`

Создание presigned URL для загрузки файла напрямую в S3/Minio.

**Request:**
```typescript
interface PresignRequest {
  filename: string;
  content_type?: string;
  size_bytes?: number;
}
```

**Response:**
```typescript
interface PresignResponse {
  upload_url: string;    // URL для загрузки
  file_id: string;       // ID файла
  fields?: object;       // Дополнительные поля для формы
}
```

### POST Callback после загрузки
**Endpoint**: `POST /api/files/v1/{file_id}/callback`

Callback вызывается после успешной загрузки файла клиентом.

**Request:**
```typescript
interface CallbackRequest {
  upload_result: object;  // Результат загрузки
}
```

### GET Получить файл
**Endpoint**: `GET /api/files/v1/{file_id}`

Получение метаданных и download URL файла.

**Response:** `FileMetadata` (см. выше)

### DELETE Удалить файл
**Endpoint**: `DELETE /api/files/v1/delete/{file_id}`

Удаление файла пользователя.

**Response:** `204 No Content`

---

## 📅 Calendars API (Календари питания)

### POST Создать календарь
**Endpoint**: `POST /api/calendars/`

Создание задачи генерации календаря питания.

**Request:**
```typescript
interface CalendarCreateRequest {
  prompt?: string;     // Текст запроса
  user_id?: string;    // ID пользователя
  preferences?: object; // Предпочтения пользователя
}
```

**Response:**
```typescript
interface CalendarCreateResponse {
  calendar_id: string;
  status: string;
  estimated_completion: string;
}
```

---

## 🔄 Batches API (Пакетная обработка)

### POST Создать batch задачу
**Endpoint**: `POST /api/batches/`

Создание новой пакетной задачи обработки.

**Request:**
```typescript
interface BatchCreateRequest {
  name: string;
  description?: string;
  config: object;     // Конфигурация обработки
  priority?: number;  // Приоритет (1-10)
}
```

**Response:**
```typescript
interface BatchCreateResponse {
  batch_id: string;
  status: string;
  created_at: string;
  estimated_duration?: number;
}
```

### GET Статус batch задачи
**Endpoint**: `GET /api/batches/{batch_id}/status`

Получение статуса пакетной задачи.

**Response:**
```typescript
interface BatchStatusResponse {
  batch_id: string;
  status: string;     // PENDING, RUNNING, COMPLETED, FAILED
  progress: number;   // 0-100
  started_at?: string;
  completed_at?: string;
  result?: object;
  error?: string;
}
```

### WebSocket: Batch Streaming
**Endpoint**: `WS /api/batches/{batch_id}/ws`

Отслеживание прогресса пакетной обработки в реальном времени.

---

## 👤 Profile API (Профиль пользователя)

### GET Получить профиль
**Endpoint**: `GET /api/profile/me`

Получение данных текущего пользователя.

**Response:**
```typescript
interface ProfileResponse {
  user_id: number;
  email: string;
  full_name?: string;
  avatar_url?: string;
  preferences?: object;
  created_at: string;
  updated_at?: string;
}
```

### PATCH Обновить профиль
**Endpoint**: `PATCH /api/profile/me`

Обновление данных профиля.

**Request:**
```typescript
interface ProfileUpdateRequest {
  full_name?: string;
  preferences?: object;
  avatar_url?: string;
}
```

**Response:** `ProfileResponse`

### DELETE Очистить историю чата
**Endpoint**: `DELETE /api/profile/me/chat-history`

Удаление всей истории чатов пользователя.

**Response:** `204 No Content`

---

## 💳 Billing API (Оплата и подписки)

### GET Планы подписок
**Endpoint**: `GET /api/billing/quotas/preview`

Получение доступных планов подписок.

**Response:**
```typescript
interface QuotaPlanResponse {
  plan_id: string;
  name: string;
  description: string;
  price_cents: number;
  currency: string;
  features: string[];
  limits: {
    monthly_launches: number;
    storage_gb: number;
  };
}
```

### POST Создать checkout сессию
**Endpoint**: `POST /api/billing/checkout`

Создание Stripe checkout сессии для оплаты.

**Request:**
```typescript
interface CheckoutRequest {
  plan_id: string;
  success_url?: string;
  cancel_url?: string;
}
```

**Response:**
```typescript
interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}
```

### POST Webhook от Stripe
**Endpoint**: `POST /api/billing/webhook`

Webhook для обработки платежей от Stripe.

**Request:** Stripe webhook payload

### GET Статистика использования
**Endpoint**: `GET /api/billing/usage`

Получение статистики использования сервисов.

**Response:**
```typescript
interface UsageStats {
  period_start: string;
  period_end: string;
  total_launches: number;
  successful_launches: number;
  failed_launches: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
}
```

---

## 🔐 Auth API (Аутентификация)

### POST Регистрация
**Endpoint**: `POST /api/auth/register`

Регистрация нового пользователя.

**Request:**
```typescript
interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}
```

**Response:**
```typescript
interface RegisterResponse {
  user_id: number;
  email: string;
  token: string;
  expires_at: string;
}
```

### POST Вход
**Endpoint**: `POST /api/auth/login`

Аутентификация пользователя.

**Request:**
```typescript
interface LoginRequest {
  email: string;
  password: string;
}
```

**Response:**
```typescript
interface LoginResponse {
  user_id: number;
  email: string;
  token: string;
  expires_at: string;
}
```

---

## 🐛 Debug API (Отладка)

### GET Debug информация
**Endpoint**: `GET /api/debug/info`

Техническая информация для отладки (только в development).

---

## 📊 Monitoring & Metrics

### Prometheus Metrics
**Endpoint**: `GET /api/metrics`

Prometheus метрики для мониторинга (если включено).

### API Documentation
**Endpoints:**
- Swagger UI: `GET /api/docs`
- OpenAPI JSON: `GET /api/openapi.json`
- ReDoc: `GET /api/redoc`

---

## 🔧 Error Handling

Все API возвращают стандартные HTTP статус коды:

- `200` - Успех
- `201` - Создано
- `204` - Нет контента
- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Запрещено
- `404` - Не найдено
- `422` - Ошибка валидации
- `500` - Внутренняя ошибка сервера

**Структура ошибок:**
```typescript
interface ErrorResponse {
  detail: string;
  errors?: object[];  // Для валидации
}
```

---

## 🚀 Production Notes

### Rate Limiting
- WebSocket: не ограничено (streaming)
- REST API: 100 запросов/минута на IP
- Files API: 10 uploads/минута на пользователя

### Timeouts
- WebSocket: соединение активно пока клиент подключен
- REST API: 30 секунд на запрос
- File uploads: 5 минут

### CORS
Разрешены origins из конфигурации (`CORS__ALLOW_ORIGINS`)

---

## 📝 Examples

### Полный чат с агентом (WebSocket)
```javascript
// 1. Подключение
const ws = new WebSocket('ws://localhost:8000/api/chats/nutrition-chat/ws?token=abc123');

// 2. Отправка сообщения
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "message",
    id: "msg-1",
    text: "Создай план питания на неделю",
    user_id: 123
  }));
};

// 3. Получение ответов
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "job_created") {
    console.log("Job started:", data.job_id);
  } else if (data.event === "agent_complete") {
    console.log("Response:", data.reply);
    if (data.file_url) {
      console.log("Download calendar:", data.file_url);
    }
  }
};
```

### Создание и отслеживание job'а
```javascript
// 1. Создать job
const jobResponse = await fetch('/api/jobs/v1/start', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    type: 'CALENDAR',
    mode: 'CHAT'
  })
});

const { job_id } = await jobResponse.json();

// 2. Подключиться к WebSocket для отслеживания
const ws = new WebSocket(`/api/jobs/v1/${job_id}/ws?token=token`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.event === "completed") {
    console.log("Job done!", data.result);
  }
};
```

---

**Документация обновляется автоматически при изменениях в API. Для вопросов обращайтесь к backend команде.**
