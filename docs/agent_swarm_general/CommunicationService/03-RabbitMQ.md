# RabbitMQ — Внутренние очереди и Celery

## Роль

RabbitMQ обеспечивает асинхронную коммуникацию между микросервисами, очереди задач Celery, обработку событий и надёжную доставку сообщений внутри платформы.

---

## Архитектура

- Exchanges: topic, direct, fanout для маршрутизации
- Durable queues с персистентными сообщениями
- Dead-letter queues (DLQ) для обработки ошибок
- High-availability mirrors для критичных очередей

---

## Интеграция с Celery

- Используется для background tasks: планирование, ретрейры, длительные операции
- Настройка retry policy, visibility timeout и rate limits

---

## Мониторинг и алерты

- Нагрузка очередей, rate of consumption, unacked messages
- Alert при резком росте DLQ или задержке обработки
