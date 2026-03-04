# Redis — Кэш и Feature Store

## Роль

Redis используется как быстрый кэш для оперативных данных, как Feature Store для ML-инференса и как Pub/Sub для быстрых событий.

---

## Структуры данных

- Hashes для хранения состяния роботов: `robot:{id}:state`
- Lists/Streams для логов и очередей событий
- Sorted Sets для управления приоритетами задач
- RedisAI/Redis-ML для простых inference задач и хранение векторов

---

## Feature Store

- Хранение агрегированных признаков для online inference
- TTL и rolling window для актуальности признаков
- Возможность хранения векторов для nearest-neighbour поиска (via Redisearch or external vector DB)

---

## Политики кэширования

- Short-lived cache для телеметрии (например, 30s)
- Long-lived cache для конфигурации и метаданных
- Invalidation: pub/sub сообщения для инвалидирования кэша
