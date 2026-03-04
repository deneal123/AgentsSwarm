# PostgreSQL — Реляционные данные

## Роль

PostgreSQL хранит транзакционные и реляционные данные: пользователи, роботы, задачи, инциденты, аудиты.

---

## Примерная схема

- `users` (id, name, role, contact, created_at)
- `robots` (id, model, status, battery, last_seen)
- `tasks` (id, type, status, assigned_robot, priority, created_at, finished_at)
- `incidents` (id, robot_id, description, severity, created_at)
- `audit_logs` (id, actor_id, action, details, timestamp)

---

## Репликация и бэкап

- WAL-репликация и горячие резервные копии
- Регулярные бэкапы на MinIO
- Миграции через миграционные скрипты (Flyway/Alembic)

---

## Индексы и оптимизация

- Partial indexes для часто используемых фильтров
- Materialized views для сложных агрегатов (репортинг)
- Vacuum/Analyze планировщик для поддержания производительности
