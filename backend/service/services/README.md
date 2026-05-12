# Services — Architectural Template

Each service domain follows **Hexagonal Architecture** (Ports & Adapters). This document describes the standard layout and rules for creating new services.

---

## Directory Structure

```
services/
└── <service_name>/
    ├── __init__.py
    ├── domain/                   # Core business logic — no framework dependencies
    │   ├── __init__.py
    │   ├── <model>.py            # Domain entities and value objects
    │   ├── <service>.py          # Pure business logic
    │   ├── exceptions.py         # Domain-specific exceptions
    │   └── contracts.py          # Domain interfaces (Protocol classes)
    │
    ├── application/              # Use cases and application services
    │   ├── __init__.py
    │   ├── <name>_service.py     # Application service — orchestrates domain + ports
    │   ├── dto.py                # Commands and query results (dataclasses)
    │   ├── mappers.py            # DTO ↔ domain model conversions
    │   ├── ports/
    │   │   ├── __init__.py
    │   │   └── interfaces.py     # Port protocols (abstract contracts for infra)
    │   └── use_cases/
    │       ├── __init__.py
    │       └── <name>_use_cases.py
    │
    ├── infrastructure/           # Adapters — external integrations
    │   ├── __init__.py
    │   ├── <worker>_tasks.py     # Celery tasks
    │   └── <adapter>.py          # Clients for external APIs, message bus, etc.
    │
    ├── persistence/              # Data access layer — repository implementations
    │   ├── __init__.py
    │   └── <name>_repository.py  # SQLAlchemy / Redis repository
    │
    └── presentation/             # HTTP and WebSocket layer — this service only
        ├── __init__.py
        ├── error_mapper.py       # Maps domain exceptions → HTTP responses
        ├── routers/
        │   ├── __init__.py
        │   └── <name>_api/
        │       ├── __init__.py
        │       ├── <name>_api.py # FastAPI router
        │       └── schemas.py    # Pydantic request/response schemas
        └── ws/
            ├── __init__.py
            └── <name>_ws.py      # WebSocket endpoint
```

---

## Layer Rules

### domain/
- **No imports** from application, infrastructure, persistence, or presentation.
- No FastAPI, SQLAlchemy, Redis, or Celery.
- Contains only Python standard library and Pydantic (for value objects).
- Domain exceptions go here (`class MyServiceError(Exception)`).

### application/
- Imports from `domain/` only (plus cross-cutting `shared/`).
- Does **not** import from `infrastructure/`, `persistence/`, or `presentation/`.
- Depends on ports (interfaces) — never on concrete implementations.
- DTOs live in `dto.py`: plain dataclasses or Pydantic models, no HTTP coupling.
- Application services receive dependencies via constructor injection.

### infrastructure/
- Implements ports defined in `application/ports/interfaces.py`.
- May import framework libraries (Celery, OpenAI SDK, MinIO, etc.).
- Does **not** import from `presentation/`.

### persistence/
- Repository classes that extend `service.repositories.base_repository.BaseRepository`.
- One repository per aggregate root.
- Use the `@connection()` decorator from `service.repositories.decorators.session_processor`.
- Raise exceptions from `service.repositories.exceptions` (not HTTP exceptions).

### presentation/
- FastAPI routers, Pydantic schemas, and WebSocket endpoints.
- Imports from `application/` (services, DTOs) and `domain/` (exceptions for mapping).
- Dependency providers go through `service.presentation.dependencies.providers`.
- Auth guard: `Depends(check_auth)` from `service.presentation.dependencies.auth_checker`.
- **Never** import from `infrastructure/` or `persistence/` directly — use injected services.

---

## Shared Utilities

| What | Where |
|------|-------|
| Base repository class | `service/shared/repositories/base_repository.py` |
| Repository exceptions | `service/shared/repositories/exceptions.py` |
| DB session decorator | `service/shared/repositories/decorators/session_processor.py` |
| Auth checker | `service/shared/security/auth_checker.py` |
| Error mapping utilities | `service/shared/error_mapper.py` |
| Global exception handler | `service/shared/presentation/handlers/exceptions_handlers.py` |
| WS message schemas | `service/shared/presentation/routers/ws_schemas.py` |
| Cross-cutting DI providers | `service/composition/state.py` |

---

## Dependency Direction

```
presentation  →  application  →  domain
infrastructure →  application  →  domain
persistence    →  (base_repository, domain models)
```

Cross-layer violations to avoid:
- `application/` importing from `presentation/` schemas — put shared request types in `application/dto.py` instead
- `domain/` importing any framework code
- `presentation/` importing directly from `persistence/` or `infrastructure/`

---

## Adding a New Service: Checklist

1. Create the directory tree above under `service/services/<name>/`.
2. Add domain entities and exceptions in `domain/`.
3. Define port protocols in `application/ports/interfaces.py`.
4. Implement the application service in `application/<name>_service.py`.
5. Add the repository in `persistence/<name>_repository.py`.
6. Implement infrastructure adapters in `infrastructure/`.
7. Create FastAPI router in `presentation/routers/<name>_api/`.
8. Wire up the service in `service/composition/` (add to `AppContainer`).
9. Register the router in `service/main.py`.
