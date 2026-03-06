# PostgreSQL — Реляционные данные

## Роль

PostgreSQL хранит транзакционные и реляционные данные: пользователи, роботы, задачи, инциденты, аудиты, конфигурации и метаданные. Взаимодействие через ORM **SQLAlchemy** (pip install sqlalchemy) с драйвером `psycopg2` или `asyncpg`.

---

## SQLAlchemy — Engine и подключение

### Engine

Engine — центральный объект для управления соединениями с БД:

`create_engine("postgresql+psycopg2://user:password@host:5432/dbname")` — создание Engine.

Формат URL: `dialect+driver://user:password@host:port/database`

| Драйвер | URL | Описание |
|---------|-----|----------|
| psycopg2 | `postgresql+psycopg2://...` | Стандартный синхронный драйвер |
| asyncpg | `postgresql+asyncpg://...` | Асинхронный драйвер (для FastAPI/asyncio) |

Параметры Engine:

- `pool_size` — размер пула соединений (по умолчанию 5)
- `max_overflow` — дополнительные соединения сверх pool_size
- `pool_timeout` — таймаут ожидания соединения из пула
- `echo=True` — логирование всех SQL-запросов (для отладки)
- `pool_pre_ping=True` — проверка живости соединения перед использованием

Engine не создаёт соединение при инициализации — соединения создаются lazy при первом запросе.

### MetaData и создание таблиц

`Base.metadata.create_all(bind=engine)` — создание всех таблиц в БД на основе объявленных моделей. Используется для инициализации БД; в production — миграции через Alembic.

---

## Declarative Mapping (ORM)

### Базовый класс

`Base = declarative_base()` — создание базового класса для всех моделей. Все модели наследуют от Base.

### Определение модели

Каждая модель — класс Python, наследующий Base:

- `__tablename__` — имя таблицы в БД
- `Column(Type, ...)` — определение столбца

### Типы столбцов

| SQLAlchemy тип | PostgreSQL тип | Описание |
|---------------|---------------|----------|
| `Integer` | INTEGER | Целое число |
| `String(N)` | VARCHAR(N) | Строка с ограничением длины |
| `Text` | TEXT | Неограниченный текст |
| `Float` | FLOAT | Число с плавающей точкой |
| `Numeric(precision, scale)` | NUMERIC | Точная десятичная дробь (для финансовых данных) |
| `Boolean` | BOOLEAN | Логическое значение |
| `DateTime` | TIMESTAMP | Дата и время |
| `LargeBinary` | BYTEA | Бинарные данные |
| `JSON` | JSON/JSONB | JSON-данные (JSONB для индексирования) |
| `ARRAY(Type)` | ARRAY | Массив (специфично для PostgreSQL) |
| `Enum(EnumClass)` | ENUM | Перечисление |

### Параметры столбцов

- `primary_key=True` — первичный ключ
- `nullable=False` — обязательное поле
- `unique=True` — уникальное значение
- `default=value` — значение по умолчанию (Python-side)
- `server_default=text("NOW()")` — значение по умолчанию (DB-side)
- `index=True` — создание индекса по столбцу
- `ForeignKey("table.column")` — внешний ключ

---

## Relationships (Связи)

### One-to-Many

`relationship("ChildModel", back_populates="parent_field")` — связь один-ко-многим. На стороне ребёнка: `ForeignKey("parent_table.id")`.

- `back_populates` — двусторонняя связь (оба класса знают друг о друге)
- `backref` — альтернатива (автоматически создаёт обратную связь на другом классе)

### Many-to-Many

Через ассоциативную таблицу: `Table("assoc", Base.metadata, Column("left_id", ForeignKey(...)), Column("right_id", ForeignKey(...)))`. Связь через `relationship("Model", secondary=assoc_table)`.

### Lazy Loading vs Eager Loading

- По умолчанию — lazy loading (подгрузка при первом обращении к атрибуту — N+1 проблема)
- `joinedload(Model.relation)` — eager loading через JOIN (одним SQL-запросом)
- `subqueryload(Model.relation)` — eager loading через подзапрос

---

## Session (Сессии)

### Создание

`Session = sessionmaker(bind=engine)` — фабрика сессий. `session = Session()` — создание сессии.

### Жизненный цикл

Сессия управляет Unit of Work — накапливает изменения и отправляет их в БД при commit:

- `session.add(object)` — добавить новый объект в сессию
- `session.add_all([obj1, obj2])` — добавить несколько объектов
- `session.commit()` — сохранить все изменения в БД
- `session.rollback()` — откатить все несохранённые изменения
- `session.close()` — закрыть сессию и вернуть соединение в пул
- `session.flush()` — отправить SQL в БД без commit (в рамках текущей транзакции)

### Context Manager

Рекомендуемый паттерн — использование `with Session() as session:` для автоматического закрытия.

### Множественные БД

Возможно привязать разные модели к разным Engine через `Session.configure(binds={Model: engine2})`. Также `sessionmaker` поддерживает deferred binding: создание без engine, привязка позже через `Session.configure(bind=engine)`.

---

## ORM Queries (Запросы)

### Базовые операции

- `session.query(Model).all()` — получить все записи
- `session.query(Model).first()` — первая запись
- `session.query(Model).one()` — ровно одна запись (исключение при 0 или >1)
- `session.query(Model).count()` — количество записей
- `session.query(Model).get(id)` — по первичному ключу

### Фильтрация

- `filter(Model.column == value)` — точное совпадение
- `filter(Model.column.like("%pattern%"))` — LIKE
- `filter(Model.column.in_([val1, val2]))` — IN
- `filter(Model.column.between(a, b))` — BETWEEN
- `filter(Model.column != None)` — IS NOT NULL
- `filter_by(column=value)` — kwargs-стиль (для простых фильтров)
- Цепочки filter: `query.filter(...).filter(...)` — AND

### Сортировка и лимиты

- `order_by(Model.column)` — ASC
- `order_by(Model.column.desc())` — DESC
- `limit(N)` — лимит
- `offset(N)` — смещение
- `slice(start, stop)` — диапазон

### JOIN

- `session.query(Model1).join(Model2)` — INNER JOIN
- `session.query(Model1).outerjoin(Model2)` — LEFT OUTER JOIN
- `joinedload(Model.relation)` — eager loading через options

### Агрегация

- `session.query(func.count(Model.id))` — COUNT
- `session.query(func.sum(Model.value))` — SUM
- `session.query(func.avg(Model.metric))` — AVG
- `group_by(Model.column)` — GROUP BY
- `having(func.count(Model.id) > N)` — HAVING

### Обновление и удаление

- `session.query(Model).filter(...).update({"column": value})` — batch UPDATE
- `session.query(Model).filter(...).delete()` — batch DELETE
- Или через объект: `obj.column = new_value; session.commit()` — UPDATE через ORM

---

## Textual SQL (Raw Queries)

`text("SELECT * FROM table WHERE id = :id")` — raw SQL-запрос с параметрами:

- Параметры через `:name` синтаксис — автоматическая защита от SQL injection
- `session.execute(text("..."), {"param": value})` — выполнение
- Результат — `CursorResult` с методами `fetchall()`, `fetchone()`, `mappings()`

Применение: сложные аналитические запросы, оконные функции, специфичные PostgreSQL-расширения (PostGIS, pg_trgm).

---

## Classical (Imperative) Mapping

Альтернативный стиль маппинга без наследования от Base:

- `Table("name", metadata, Column(...), ...)` — определение таблицы отдельно
- `mapper_registry.map_imperatively(PythonClass, table)` — привязка Python-класса к таблице
- Полезно когда Python-классы должны быть независимы от ORM (clean architecture)

---

## Схема данных AgentsSwarm

### Основные таблицы

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `users` | Операторы и администраторы | id, name, email, role, password_hash, created_at, is_active |
| `robots` | Регистрация роботов | id, model, serial_number, status (enum), battery_level, zone_id, last_seen, config (JSONB) |
| `tasks` | Задачи для роботов | id, type, status (enum), assigned_robot_id (FK), priority, params (JSONB), created_at, started_at, finished_at, result (JSONB) |
| `incidents` | Аварийные ситуации | id, robot_id (FK), description, severity (enum), resolved_at, resolution_notes |
| `audit_logs` | Журнал действий | id, actor_id (FK), action, target_type, target_id, details (JSONB), timestamp |
| `zones` | Рабочие зоны | id, name, boundaries (JSONB), type, max_robots |
| `model_versions` | Версии ML-моделей | id, model_name, version, minio_path, status, deployed_at, metrics (JSONB) |
| `configurations` | Конфигурации системы | id, service_name, config_key, config_value (JSONB), updated_at, updated_by (FK) |

### Связи

- `robots` → `zones`: Many-to-One (каждый робот в одной зоне)
- `tasks` → `robots`: Many-to-One (задача назначена одному роботу)
- `tasks` → `users`: Many-to-One (задача создана пользователем)
- `incidents` → `robots`: Many-to-One (инцидент связан с роботом)
- `audit_logs` → `users`: Many-to-One (действие совершено пользователем)

### Enum-типы

- `RobotStatus`: IDLE, ACTIVE, CHARGING, MAINTENANCE, ERROR, OFFLINE
- `TaskStatus`: PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
- `IncidentSeverity`: LOW, MEDIUM, HIGH, CRITICAL
- `UserRole`: OPERATOR, SUPERVISOR, ADMIN

### JSONB-поля

PostgreSQL JSONB используется для полуструктурированных данных:

- `robots.config` — специфичная конфигурация робота (зависит от модели)
- `tasks.params` — параметры задачи (зависят от типа)
- `tasks.result` — результат выполнения
- `audit_logs.details` — детали действия

JSONB поддерживает GIN-индексы для эффективного поиска по вложенным полям.

---

## Миграции (Alembic)

Alembic — инструмент миграций для SQLAlchemy:

- `alembic init` — инициализация каталога миграций
- `alembic revision --autogenerate -m "description"` — автогенерация миграции на основе diff между моделями и текущим состоянием БД
- `alembic upgrade head` — применить все миграции до последней
- `alembic downgrade -1` — откатить последнюю миграцию
- `alembic history` — история миграций

Каждая миграция содержит функции `upgrade()` и `downgrade()` — двусторонние изменения схемы.

Применение: все изменения схемы БД проходят через Alembic-миграции, автоматически применяемые при развёртывании через CI/CD.

---

## Репликация и бэкап

### WAL-репликация

- Streaming Replication: primary → standby через WAL (Write-Ahead Log)
- Синхронная и асинхронная репликация
- Hot Standby — replica доступна для чтения

### Бэкапы

- pg_dump / pg_basebackup для регулярных бэкапов
- Бэкапы сохраняются в MinIO (бакет `backups`)
- Point-in-Time Recovery (PITR) через WAL-архив

---

## Индексы и оптимизация

### Типы индексов

| Тип | Применение |
|-----|-----------|
| B-tree (по умолчанию) | Стандартные поиск/сортировка |
| GIN | JSONB-поля, полнотекстовый поиск, массивы |
| GiST | Геопространственные данные (PostGIS), диапазоны |
| BRIN | Большие таблицы с естественной сортировкой (временные ряды) |
| Hash | Exact-match поиск |

### Partial Indexes

Индекс только по подмножеству строк: `CREATE INDEX ON tasks (...) WHERE status = 'PENDING'` — индексирует только активные задачи, экономит место.

### Materialized Views

Предвычисленные агрегаты для Dashboard:

- Количество роботов по статусам
- Средняя длительность задач по типам
- Статистика инцидентов за период

Обновление: `REFRESH MATERIALIZED VIEW CONCURRENTLY` — без блокировки чтения.

---

## Интеграция с сервисами

### Gateway Service

FastAPI dependency injection: `session = Depends(get_db)` — сессия создаётся на каждый HTTP-запрос и закрывается после ответа.

### Orchestrator

- Задачи создаются и обновляются через SQLAlchemy ORM
- Статусы задач меняются атомарно (SELECT FOR UPDATE при необходимости)
- Результаты инференса сохраняются в JSONB-поле `tasks.result`

### Redis Cache

Паттерн Cache-Aside:

- Чтение: сначала Redis → если cache miss → PostgreSQL → записать в Redis
- Запись: записать в PostgreSQL → инвалидировать Redis через Pub/Sub
- TTL в Redis: 5 минут для часто запрашиваемых данных (список роботов, активные задачи)

---

## Best Practices

- JSONB для полуструктурированных данных вместо множества nullable-столбцов
- GIN-индексы на JSONB-поля для эффективного поиска
- Enum-типы для конечных множеств значений (статусы, роли, severity)
- Partial indexes для фильтров по статусам (большинство запросов — по активным сущностям)
- Alembic для всех миграций — автогенерация + ручная проверка
- `pool_pre_ping=True` для устойчивости к разрыву соединений
- Materialized Views для тяжёлых агрегатов на Dashboard
- PITR через WAL-архив в MinIO для disaster recovery
- `text()` с параметрами для raw SQL — защита от SQL injection
- `joinedload()` для eager loading — избежание N+1 проблемы
- Vacuum/Analyze планировщик для поддержания производительности
