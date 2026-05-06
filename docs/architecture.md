# Архитектура GPTHub

**Последнее обновление:** 2026-04-23

## Контрактный pipeline API

- Источник правды контракта: `FastAPI app.openapi()` из `backend/service/main.py`.
- В CI OpenAPI генерируется командой `python scripts/export_openapi.py --output artifacts/openapi.json`.
- Для критичных операций используется snapshot-проверка `backend/tests/test_critical_endpoint_snapshots.py`.
- Для DTO-моделей ответов используется snapshot-проверка `backend/tests/test_response_schema_snapshots.py`.
- При изменении контракта разработчик обновляет snapshots и документацию `docs/api.md`, `docs/architecture.md`.

## Стабилизированные зоны контракта

К критичным операциям, которые защищены endpoint-snapshot тестом, относятся:

- `POST /api/auth/v1/register`
- `POST /api/auth/v1/login`
- `POST /api/chats/`
- `GET /api/chats/{thread_id}`
- `POST /api/chats/{thread_id}/message`
- `POST /api/jobs/v1/start`
- `GET /api/jobs/v1/result/{job_id}`



## ADR-практика

- ADR хранятся в `docs/adr/`.
- Каждое крупное изменение архитектурного слоя обязательно сопровождается новым ADR.
- Базовые решения по quality gates и метрикам сложности описаны в `docs/adr/0001-quality-gates-and-complexity-metrics.md`.

## Безопасный lifecycle enum в БД

- Enum-контракт приложения фиксируется в `backend/service/models/key_value.py`.
- Enum-контракт схемы фиксируется ревизиями Alembic в `backend/alembic/versions/`.
- Тест `backend/tests/test_enum_schema_contract.py` вычисляет набор значений enum из SQLAlchemy metadata и сравнивает его с итоговым состоянием по цепочке Alembic ревизий.
- CI шаг `python scripts/check_enum_revision_guard.py <base> <head>` блокирует PR, если enum-модели изменены без новой ревизии в `backend/alembic/versions/`.
- Для каждого enum-change используется шаблон `backend/alembic/templates/enum_change_template.py` с обязательными блоками `upgrade`, `downgrade`, `backfill`, `data-check`.

## Mermaid: верхнеуровневая схема проекта

```mermaid
graph TB
	User["User / Browser"]
	Frontend["Frontend\nReact + Chakra UI"]
	Api["Backend API\nFastAPI routers"]

	Services["Service layer\nchat/job/profile flows"]
	Agents["Agents layer\norchestrator + processor + subagents + tools"]
	Repos["Repositories"]
	Infra["Infrastructure adapters"]

	DB["PostgreSQL"]
	Redis["Redis\ncache + streams"]
	Celery["Celery workers"]
	Storage["MinIO / Local Storage"]
	LLM["LLM providers\nOpenAI / MWS"]

	Docs["docs/"]
	Tests["backend/tests"]

	User -->|"1. HTTP/WebSocket"| Frontend
	Frontend -->|"2. API calls"| Api
	Api -->|"3. use-cases"| Services

	Services -->|"4a. agent processing"| Agents
	Services -->|"4b. persistence"| Repos
	Services -->|"4c. integration layer"| Infra

	Infra -->|"5. data"| DB
	Infra -->|"5. events/cache"| Redis
	Infra -->|"5. async jobs"| Celery
	Infra -->|"5. files"| Storage

	Celery -->|"6. invoke"| Agents
	Agents -->|"7. model/tool calls"| LLM

	Services -.->|"8. design reference"| Docs
	Services -.->|"9. quality checks"| Tests

	style User fill:#ff6b6b,stroke:#ff6b6b,stroke-width:2px,color:#fff
	style Frontend fill:#ff6b6b,stroke:#ff6b6b,stroke-width:2px,color:#fff

	style Api fill:#4a9eff,stroke:#4a9eff,stroke-width:2px,color:#fff
	style Services fill:#4a9eff,stroke:#4a9eff,stroke-width:2px,color:#fff
	style Repos fill:#4a9eff,stroke:#4a9eff,stroke-width:2px,color:#fff

	style Agents fill:#52c41a,stroke:#52c41a,stroke-width:2px,color:#fff

	style Infra fill:#9b59b6,stroke:#9b59b6,stroke-width:2px,color:#fff
	style DB fill:#9b59b6,stroke:#9b59b6,stroke-width:2px,color:#fff
	style Redis fill:#9b59b6,stroke:#9b59b6,stroke-width:2px,color:#fff
	style Celery fill:#9b59b6,stroke:#9b59b6,stroke-width:2px,color:#fff
	style Storage fill:#9b59b6,stroke:#9b59b6,stroke-width:2px,color:#fff

	style LLM fill:#e67e22,stroke:#e67e22,stroke-width:2px,color:#fff
	style Docs fill:#ffa500,stroke:#ffa500,stroke-width:2px,color:#fff
	style Tests fill:#ffa500,stroke:#ffa500,stroke-width:2px,color:#fff
```

## C4: Container boundaries after application services split

```mermaid
graph LR
    User["User"]
    FE["Frontend SPA"]
    API["FastAPI Routers<br/>transport only"]
    APP["Application Services<br/>chat_application_service<br/>job_application_service"]
    DOMAIN["Domain Services<br/>chat/job/process handlers"]
    PORTS["Ports Interfaces<br/>ChatCommandPort<br/>JobOrchestrationPort<br/>AgentExecutionPort"]
    INFRA["Infrastructure Adapters<br/>celery/redis/storage/db"]
    AGENTS["Agents Runtime"]
    EXT["LLM Providers"]

    User --> FE --> API
    API --> APP
    APP --> DOMAIN
    DOMAIN --> PORTS
    INFRA --> PORTS
    AGENTS --> PORTS
    INFRA --> EXT
    AGENTS --> EXT
```

## Flow: Chat message orchestration with error mapping

```mermaid
sequenceDiagram
    participant R as chat_api router
    participant A as ChatApplicationService
    participant C as ChatService
    participant H as ProcessChatMessageHandler
    participant Q as JobQueuePort
    participant M as chat_exceptions mapper

    R->>A: post_message(payload)
    A->>C: post_message(context)
    C->>H: dispatch_and_wait(command)
    H->>Q: enqueue_process_agent_message
    Q-->>H: result
    H-->>C: ChatReplyResult
    C-->>A: ChatReplyResult
    A-->>R: DTO
    Note over A,M: Any domain exception<br/>mapped in map_chat_exception_to_http
```

## UI boundaries (enforced)
- All reusable UI components are located only in `frontend/src/shared/ui`.
- Feature modules must not import components from other features directly; shared UI is consumed via `@shared/ui/*` public API only.
