# ADR-0003: Backend refactor scope, contract freeze, and composition root split

- Статус: Accepted
- Дата: 2026-05-08

## Контекст

Для backend-модулей требовалась единая и проверяемая структура слоёв, чтобы зафиксировать границы между transport, use-cases, domain и адаптерами.

## Решение

### 1) Стандарт структуры модулей

Принят обязательный стандарт:

`backend/service/services/<module>/{domain,application,infrastructure,presentation}`

Стандарт применяется для модулей:

- `agents`
- `jobs`
- `files`
- `profile`
- `analytics`
- `chat`

### 2) Карта текущего состояния

Актуальная карта файлов по слоям для модулей `agents`, `jobs`, `files`, `profile`, `analytics`, `chat` поддерживается в `docs/architecture.md` и является baseline для последующих миграций.

### 3) Правила зависимостей

Зафиксированы инварианты зависимостей:

1. `presentation -> application`
2. `application -> domain + ports`
3. `infrastructure -> application ports/domain`
4. Запрещены прямые зависимости:
   - `presentation -> infrastructure`
   - `domain -> infrastructure`

### 4) Composition root

Composition root остаётся split по модулям:

- `service/composition/infra.py`
- `service/composition/repositories.py`
- `service/composition/services.py`
- `service/composition/state.py`
- `service/container.py` как compatibility facade

## Последствия

- Зафиксирована целевая схема слоёв для всех ключевых backend-модулей.
- Документация отражает актуальное распределение файлов по слоям.
- Появился единый набор правил зависимостей для code review и дальнейшего рефакторинга.
