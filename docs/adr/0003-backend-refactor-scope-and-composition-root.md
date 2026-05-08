# ADR-0003: Backend refactor scope, contract freeze, and composition root split

- Статус: Accepted
- Дата: 2026-05-08

## Контекст

Текущий backend содержит смешение стилей модульной структуры и перегруженный composition root:

- `service/presentation/routers/*` сосуществует с feature-style `service/services/*/presentation/*`.
- `service/container.py` одновременно отвечает за bootstrap infrastructure, создание repositories и сервисов, а также за FastAPI dependency providers.
- В роутерах встречается бизнес/интеграционная логика, что усложняет transport boundary.
- Есть drift по путям в документации и stale import в jobs-роутере.

Проект уже фиксирует обязательность ADR для крупных layer changes (`ADR-0002`), поэтому рефакторинг должен быть формализован до и во время изменений.

## Решение

### 1) Scope и ограничения (phase-1)

Цели фазы:

1. Архитектурная консистентность слоёв.
2. Надёжность bootstrap/startup пути.
3. Улучшение тестопригодности composition root и providers.

Ограничения:

- Внешние контракты API/WS не меняются без отдельного согласования.
- Семантика auth и background jobs сохраняется.
- Обратная совместимость import-path для существующих модулей сохраняется через compatibility facade.

### 2) Baseline и риски

Зафиксированные зоны риска:

- Mixed package styles: `service/presentation/*` и `service/services/*/presentation`.
- Overloaded composition root: монолитный `service/container.py`.
- Cross-feature coupling: `service/main.py` агрегирует множество routers, chat router содержит tool/business вызовы.
- Stale import: `jobs_api.py` ссылался на отсутствующий `service.application.job_application_service`.
- Docs drift: `docs/architecture.md` ссылался на неактуальные `backend/service/chat/*`.

### 3) Целевое состояние архитектуры

Для feature-доменов фиксируется единый набор слоёв:

- `presentation` — transport only.
- `application` — use-cases/orchestration.
- `domain` — business rules.
- `infrastructure/persistence` — adapters.

Composition root выносится в отдельный пакет с малыми модулями:

- infra bootstrap,
- repositories factory,
- services factory,
- state/providers.

`service/container.py` остаётся как compatibility facade.

### 4) План выполнения (waves)

- Wave A: stabilization (import path drift + dependency entrypoints).
- Wave B: composition split на `service/composition/*`.
- Wave C: feature boundaries для jobs/chat (первая волна).
- Wave D: router cleanup (transport-only handlers).
- Wave E: cross-cutting hardening (config access, error/logging consistency).
- Wave F: docs + ADR synchronization.

### 5) Non-regression quality gates

Обязательные проверки на каждой волне:

- `ruff`, `mypy`, `pytest` из `backend/`.
- Snapshot-защита контрактов:
  - `backend/tests/test_critical_endpoint_snapshots.py`
  - `backend/tests/test_response_schema_snapshots.py`
- Enum/schema contract:
  - `backend/tests/test_enum_schema_contract.py`
  - `backend/scripts/check_enum_revision_guard.py`
- Coverage gate из `pytest.ini` сохраняется.

## Последствия

- Composition root стал модульным и проще для изменения/тестирования.
- Маршрут постепенной миграции к единым layer boundaries зафиксирован.
- Документация и ADR синхронизированы с текущей фазой рефакторинга.
