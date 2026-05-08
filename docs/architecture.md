# Архитектура GPTHub

**Последнее обновление:** 2026-05-08

## Стандарт backend-модуля

## План миграции по волнам

- **Wave 1 (низкий риск):** `files`, `profile`, `analytics`
- **Wave 2:** `jobs`
- **Wave 3 (высокий риск):** `agents`, `chat`

Порядок работ для каждой волны:

1. Интерфейсы и use-case (`application`).
2. Адаптеры (`infrastructure`).
3. Presentation-слой (`presentation`).

На переходном этапе сохраняются временные фасады и deprecated-импорты до полного перевода call-sites. После каждой волны обновляются тесты `backend/tests/`, архитектурные правила и ADR.


Базовый стандарт для feature-модулей backend:

`backend/service/services/<module>/{domain,application,infrastructure,presentation}`

Допустимые дополнительные подпакеты внутри слоёв (например `application/ports`, `presentation/routers`, `infrastructure/chat_worker`) не нарушают стандарт, если сохраняют направление зависимостей.

## Карта текущих модулей и слоёв

### agents

- `presentation`
  - `backend/service/services/agents/presentation/__init__.py`
- `application`
  - `backend/service/services/agents/application/__init__.py`
  - `backend/service/services/agents/application/agent_execution_service.py`
  - `backend/service/services/agents/application/agent_file_bridge.py`
  - `backend/service/services/agents/application/agent_session_service.py`
  - `backend/service/services/agents/application/model_routing_service.py`
  - `backend/service/services/agents/application/ports/__init__.py`
  - `backend/service/services/agents/application/ports/interfaces.py`
- `domain`
  - `backend/service/services/agents/domain/__init__.py`
  - `backend/service/services/agents/base_agent.py`
  - `backend/service/services/agents/chat_agent.py`
  - `backend/service/services/agents/events.py`
  - `backend/service/services/agents/orchestrator.py`
  - `backend/service/services/agents/processor.py`
  - `backend/service/services/agents/runner.py`
  - `backend/service/services/agents/sessions.py`
  - `backend/service/services/agents/pipeline/__init__.py`
  - `backend/service/services/agents/pipeline/context_enricher.py`
  - `backend/service/services/agents/pipeline/error_handling.py`
  - `backend/service/services/agents/pipeline/event_stream.py`
  - `backend/service/services/agents/pipeline/postprocess.py`
  - `backend/service/services/agents/pipeline/processor_flow.py`
  - `backend/service/services/agents/routing/__init__.py`
  - `backend/service/services/agents/routing/constants.py`
  - `backend/service/services/agents/routing/policy.py`
  - `backend/service/services/agents/routing/router_agent.py`
  - `backend/service/services/agents/guardrails/__init__.py`
  - `backend/service/services/agents/guardrails/response_guardrails.py`
  - `backend/service/services/agents/subagents/__init__.py`
  - `backend/service/services/agents/subagents/audio_transcribe.py`
  - `backend/service/services/agents/subagents/base.py`
  - `backend/service/services/agents/subagents/deep_research.py`
  - `backend/service/services/agents/subagents/factory.py`
  - `backend/service/services/agents/subagents/general.py`
  - `backend/service/services/agents/subagents/image_generation.py`
  - `backend/service/services/agents/subagents/pptx_generation.py`
  - `backend/service/services/agents/subagents/utils.py`
  - `backend/service/services/agents/subagents/web_search.py`
  - `backend/service/services/agents/tools/__init__.py`
  - `backend/service/services/agents/tools/deep_research.py`
  - `backend/service/services/agents/tools/function_tools.py`
  - `backend/service/services/agents/tools/pptx.py`
  - `backend/service/services/agents/tools/router.py`
  - `backend/service/services/agents/tools/web_search.py`
  - `backend/service/services/agents/pydantic/__init__.py`
  - `backend/service/services/agents/pydantic/agents.py`
  - `backend/service/services/agents/pydantic/sessions.py`
- `infrastructure`
  - `backend/service/services/agents/infrastructure/__init__.py`
  - `backend/service/services/agents/client/__init__.py`
  - `backend/service/services/agents/client/mws_client.py`
  - `backend/service/services/agents/client/openai_client.py`
  - `backend/service/services/agents/client/openrouter_client.py`
  - `backend/service/services/agents/integration/__init__.py`
  - `backend/service/services/agents/integration/base.py`
  - `backend/service/services/agents/integration/memory.py`

### jobs

- `presentation`
  - `backend/service/services/jobs/presentation/__init__.py`
- `application`
  - `backend/service/services/jobs/application/__init__.py`
  - `backend/service/services/jobs/application/job_application_service.py`
  - `backend/service/services/jobs/application/job_processor.py`
  - `backend/service/services/jobs/application/job_service.py`
  - `backend/service/services/jobs/application/ports/__init__.py`
  - `backend/service/services/jobs/application/ports/interfaces.py`
- `domain`
  - `backend/service/services/jobs/domain/__init__.py`
- `infrastructure`
  - `backend/service/services/jobs/infrastructure/__init__.py`

### files

- `presentation`
  - `backend/service/services/files/presentation/__init__.py`
- `application`
  - `backend/service/services/files/application/__init__.py`
  - `backend/service/services/files/application/file_saver_service.py`
  - `backend/service/services/files/application/file_scanner_service.py`
  - `backend/service/services/files/application/ports/__init__.py`
  - `backend/service/services/files/application/ports/interfaces.py`
- `domain`
  - `backend/service/services/files/domain/__init__.py`
- `infrastructure`
  - `backend/service/services/files/infrastructure/__init__.py`

### profile

- `presentation`
  - `backend/service/services/profile/presentation/__init__.py`
- `application`
  - `backend/service/services/profile/application/__init__.py`
  - `backend/service/services/profile/application/auth_service.py`
  - `backend/service/services/profile/application/profile_service.py`
- `domain`
  - `backend/service/services/profile/domain/__init__.py`
- `infrastructure`
  - `backend/service/services/profile/infrastructure/__init__.py`

### analytics

- `presentation`
  - `backend/service/services/analytics/presentation/__init__.py`
- `application`
  - `backend/service/services/analytics/application/__init__.py`
  - `backend/service/services/analytics/application/memory_service.py`
- `domain`
  - `backend/service/services/analytics/domain/__init__.py`
- `infrastructure`
  - `backend/service/services/analytics/infrastructure/__init__.py`

### chat

- `presentation`
  - `backend/service/services/chat/presentation/__init__.py`
  - `backend/service/services/chat/presentation/error_mapper.py`
  - `backend/service/services/chat/presentation/http/upload_api.py`
  - `backend/service/services/chat/presentation/routers/__init__.py`
  - `backend/service/services/chat/presentation/routers/chat_api/chat_api.py`
  - `backend/service/services/chat/presentation/routers/chat_api/schemas.py`
  - `backend/service/services/chat/presentation/routers/chat_ws.py`
  - `backend/service/services/chat/presentation/ws/__init__.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/__init__.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/auth.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/connection.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/message_handler.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/metrics.py`
  - `backend/service/services/chat/presentation/ws/chat_ws/stream_consumer.py`
- `application`
  - `backend/service/services/chat/application/__init__.py`
  - `backend/service/services/chat/application/chat_application_service.py`
  - `backend/service/services/chat/application/use_cases/chat_use_cases.py`
  - `backend/service/services/chat/application/use_cases/upload_file_use_case.py`
  - `backend/service/services/chat/application/ports/__init__.py`
  - `backend/service/services/chat/application/ports/chat_ports.py`
  - `backend/service/services/chat/application/ports/interfaces.py`
  - `backend/service/services/chat/application/ports/media_analysis_port.py`
- `domain`
  - `backend/service/services/chat/domain/__init__.py`
  - `backend/service/services/chat/domain/chat_contracts.py`
  - `backend/service/services/chat/domain/chat_exceptions.py`
  - `backend/service/services/chat/domain/chat_fallback_service.py`
  - `backend/service/services/chat/domain/chat_job_orchestrator.py`
  - `backend/service/services/chat/domain/chat_service.py`
  - `backend/service/services/chat/domain/process_chat_message_handler.py`
- `infrastructure`
  - `backend/service/services/chat/infrastructure/__init__.py`
  - `backend/service/services/chat/infrastructure/chat_worker_tasks.py`
  - `backend/service/services/chat/infrastructure/chat_worker/__init__.py`
  - `backend/service/services/chat/infrastructure/chat_worker/factory.py`
  - `backend/service/services/chat/infrastructure/chat_worker/services.py`
  - `backend/service/services/chat/infrastructure/media/openai_media_analysis_adapter.py`
  - `backend/service/services/chat/persistence/__init__.py`
  - `backend/service/services/chat/persistence/chat_persistence_service.py`
  - `backend/service/services/chat/persistence/chat_repository.py`
  - `backend/service/services/chat/persistence/chat_worker_repository.py`

## Правила зависимостей (обязательные)

1. `presentation -> application`
2. `application -> domain + ports`
3. `infrastructure -> application ports/domain`
4. Запрещены прямые зависимости:
   - `presentation -> infrastructure`
   - `domain -> infrastructure`

## Composition root

- `backend/service/composition/infra.py` — bootstrap infra adapters.
- `backend/service/composition/repositories.py` — repositories factory.
- `backend/service/composition/services.py` — services/application factory.
- `backend/service/composition/state.py` — container state + FastAPI providers.
- `backend/service/container.py` — compatibility facade.
