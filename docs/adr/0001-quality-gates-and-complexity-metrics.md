# ADR-0001: Quality gates и метрики сложности модулей

- Статус: Accepted
- Дата: 2026-04-23

## Контекст

Нужно зафиксировать ограничители роста сложности и единые quality gates для backend и frontend.

## Решение

1. Backend quality gates:
   - `ruff` с ограничением `max-cyclomatic-complexity=70`.
   - `mypy` для критических пакетов `service.services`, `service.agents`.
   - `pytest` с coverage gate по критическим пакетам и `--cov-fail-under=85`.
   - скрипт `backend/scripts/check_module_complexity.py` для:
     - max lines per file,
     - max function length,
     - max cyclomatic complexity,
     - max import fan-in/fan-out для критических модулей.

2. Frontend quality gates:
   - `eslint` с обязательным `react-hooks/exhaustive-deps`.
   - ограничение размеров файлов и функций.
   - запрет логики и прямого импорта API/hooks/services в `src/pages/**`.

3. Pre-commit и CI:
   - pre-commit hooks для backend/frontend.
   - единый workflow lint + typecheck + tests + snapshots + OpenAPI diff.

## Последствия

- Изменения, увеличивающие сложность выше порогов, блокируются на pre-commit и CI.
- Контракт API и критичные DTO остаются контролируемыми через snapshot-проверки.
