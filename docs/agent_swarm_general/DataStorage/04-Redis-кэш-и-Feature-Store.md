# Redis — Кэш и Feature Store

## Роль

Redis используется как быстрый in-memory кэш для оперативных данных, как Feature Store для ML-инференса, как Pub/Sub брокер для быстрых событий, и как TimeSeries/Streams хранилище. Взаимодействие через Python-клиент **redis-py** (модуль `redis`) с поддержкой синхронного и асинхронного (asyncio) режимов.

---

## Клиент redis-py

### Подключение

Основной класс — `redis.Redis`. Параметр `decode_responses=True` автоматически декодирует bytes в строки.

Варианты подключения:

| Способ | Описание |
|--------|----------|
| `redis.Redis(host, port, decode_responses=True)` | Прямое подключение к одному экземпляру |
| `redis.from_url("redis://localhost:6379?decode_responses=True")` | Подключение по URL |
| `redis.Redis(connection_pool=pool)` | Подключение через общий ConnectionPool |
| `redis.Redis.from_pool(pool)` | Клиент берёт ownership над пулом (закрывает при aclose) |

Схемы URL:

- `redis://` — TCP-подключение
- `rediss://` — TCP + TLS (SSL)
- `unix://` — Unix Domain Socket

### Протокол RESP

По умолчанию — RESP v2. Для включения RESP v3: `redis.Redis(protocol=3)` или `redis://...?protocol=3`.

### Asyncio

Модуль `redis.asyncio` предоставляет асинхронный клиент. Все команды — корутины. Требуется явное закрытие через `await client.aclose()`:

- `redis.asyncio.Redis()` — async-клиент
- `redis.asyncio.ConnectionPool.from_url(...)` — async пул подключений
- При общем ConnectionPool для нескольких клиентов — закрывать пул отдельно через `await pool.aclose()`

### Sentinel (High Availability)

`redis.asyncio.sentinel.Sentinel([("host", 26379)])` — клиент для Redis Sentinel:

- Автоматическое обнаружение master/slave
- `sentinel.master_for("mymaster")` — клиент для записи (master)
- `sentinel.slave_for("mymaster")` — клиент для чтения (slave)
- Автоматическое переключение при failover

---

## Структуры данных

### Strings (базовые ключ-значение)

- `set(key, value)` — установить значение
- `get(key)` — получить значение (None для несуществующих ключей)
- `setex(key, seconds, value)` — установить с TTL
- `exists(key)` — проверка существования (возвращает 1 или 0)
- `mset(dict)` — установить несколько ключей за одну операцию
- `mget(key1, key2, ...)` — получить несколько значений (None для отсутствующих)
- `ttl(key)` — оставшееся время жизни ключа

### Hashes (состояние роботов)

Используются для хранения структурированного состояния робота: `robot:{id}:state`

- `hset(name, mapping={"field": "value", ...})` — установить поля
- `hget(name, key)` — получить одно поле
- `hgetall(name)` — получить все поля

В AgentsSwarm: текущее состояние каждого робота хранится как Hash с полями: `status`, `battery`, `position_x`, `position_y`, `zone_id`, `last_seen`, `current_task`.

### Lists и Sorted Sets

- **Lists** — для очередей событий, FIFO-логов
- **Sorted Sets** — для управления приоритетами задач (score = priority, member = task_id)

### JSON (RedisJSON)

- `r.json().set(key, Path.root_path(), dict)` — сохранить JSON-документ
- `r.json().get(key)` — получить документ
- Поддержка JSONPath для доступа к вложенным полям

---

## Pipelines — Пакетные операции

Pipelines группируют несколько Redis-команд в один запрос, значительно снижая сетевой overhead. Команды буферизуются в памяти и отправляются в одном TCP-запросе через Redis Bulk String Protocol.

- `pipe = r.pipeline()` — создание pipeline
- `pipe.set("a", "value").get("a").execute()` — chained вызов с финальным execute()
- `pipe.execute()` — возвращает список результатов всех команд в порядке добавления

Производительность: 100000 INCR операций без pipeline — ~22 секунды; с pipeline — ~2.4 секунды (**10x ускорение**).

### Transactions (Multi/Exec)

Pipeline с параметром `transaction=True` оборачивает команды в MULTI/EXEC — атомарное выполнение. Для asyncio: `async with r.pipeline(transaction=True) as pipe`.

Применение в AgentsSwarm:

- Атомарное обновление состояния робота (несколько полей Hash)
- Batch-обновление Feature Store перед инференсом
- Атомарная запись связанных ключей (состояние + метрики + timestamp)

---

## Streams

Redis Streams — это append-only структура данных для потоковой обработки событий. Каждое сообщение в потоке имеет уникальный auto-generated ID (timestamp-sequence).

### Базовые операции

- `xadd(stream_key, {"field": "value"})` — добавить сообщение в поток
- `xlen(stream_key)` — длина потока
- `xread(count=N, streams={key: id})` — прочитать N сообщений начиная с id
- `xread(count=1, block=5000, streams={key: '$'})` — блокирующее ожидание новых сообщений (5 секунд)
- `xread(count=1, streams={key: '+'})` — последнее доступное сообщение
- Чтение из нескольких потоков одновременно через `streams={key1: id1, key2: id2}`

### Consumer Groups

Consumer Groups обеспечивают распределённую обработку потока между несколькими consumer'ами:

- `xgroup_create(name, groupname, id)` — создать группу для потока (id=0 для чтения с начала)
- `xreadgroup(groupname, consumername, count, streams={key: '>'})` — прочитать новые (не доставленные) сообщения для consumer'а в группе
- Несколько consumer'ов в одной группе — **load balancing** (каждое сообщение получает только один consumer)
- Несколько групп на одном потоке — **fan-out** (каждая группа получает все сообщения независимо)

### Acknowledgment и Pending

- `xack(stream_key, group, message_id)` — подтвердить обработку сообщения
- `xpending(name, groupname)` — количество неподтверждённых (pending) сообщений
- До xack сообщение остаётся в pending-списке и может быть перечитано при перезапуске consumer'а
- `xdel(stream_key, message_id)` — физическое удаление сообщения из потока (после xack всех групп)

Применение в AgentsSwarm:

- Поток событий роботов: `robot_events_stream` — группа для логирования, группа для мониторинга, группа для аналитики
- Поток результатов инференса: consumer group с несколькими обработчиками для параллельной обработки
- Поток команд: одна группа на Orchestrator — fair dispatch между воркерами

---

## TimeSeries (Redis TimeSeries)

Модуль RedisTimeSeries для хранения и агрегации временных рядов внутри Redis.

### Операции

- `ts.create(key)` — создать TimeSeries ключ
- `ts.create(key, retention_msecs=N)` — с автоматическим удалением данных старше N мс
- `ts.create(key, labels={"label": "value"})` — с метками для фильтрации
- `ts.add(key, timestamp, value)` — добавить точку (timestamp: UNIX ms или `*` для серверного времени)
- `ts.get(key)` — последняя точка: (timestamp, value)
- `ts.range(key, "-", "+")` — все точки от начала до конца
- `ts.range(key, from_ts, to_ts)` — диапазон
- `ts.delete(key, from_ts, to_ts)` — удалить точки в диапазоне
- `ts.madd([(key1, ts, val), (key2, ts, val)])` — batch-добавление в несколько TimeSeries
- `ts.incrby(key, value)` — инкрементальное обновление (для счётчиков)
- `ts.mget(["label=value"])` — получить последние точки по фильтру меток (кросс-ключевой запрос)
- `ts.mget(["label=value"], with_labels=True)` — с включением меток в результат

### Retention Policy

Retention задаётся при создании ключа или при добавлении точки. Устаревшие записи удаляются **при добавлении новой точки** (не по таймеру).

### Duplicate Policy

По умолчанию — `BLOCK` (дубликаты timestamp запрещены). Альтернативы: `LAST` (оставить последнее), `FIRST` (оставить первое), `MIN`, `MAX`, `SUM`.

Применение в AgentsSwarm:

- Краткосрочные высокочастотные метрики (позиция робота с частотой 50 Гц, retention 60 секунд)
- Dashboard real-time графики: ts.range() за последние N секунд
- Кросс-роботовые метрики через labels: `ts.mget(["robot_type=manipulator"])` — последние значения всех манипуляторов

---

## Pub/Sub

Redis Pub/Sub — легковесный механизм рассылки сообщений:

- `r.pubsub()` — создание подписчика
- `pubsub.subscribe("channel:1", "channel:2")` — подписка на конкретные каналы
- `pubsub.psubscribe("channel:*")` — подписка по шаблону (glob-style)
- `r.publish("channel:1", "message")` — публикация
- `pubsub.get_message(ignore_subscribe_messages=True, timeout=None)` — получение сообщения

В asyncio: полностью совместимый async API с `async with r.pubsub() as pubsub`.

Применение в AgentsSwarm:

- Инвалидация кэша: publish события при изменении данных в PostgreSQL/InfluxDB
- Real-time уведомления для Dashboard: статус роботов, завершение задач
- Координация между сервисами: сигналы обновления конфигурации

---

## Search (RediSearch)

Модуль RediSearch позволяет создавать индексы и выполнять полнотекстовый поиск, фильтрацию и агрегацию над JSON-документами:

- `r.ft().create_index(schema, definition)` — создать индекс с определёнными полями (TextField, NumericField, TagField)
- `r.ft().search("query")` — простой текстовый поиск
- `r.ft().search(Query("...").add_filter(NumericFilter(...)))` — с числовыми фильтрами
- `r.ft().search(Query("*").paging(offset, num).sort_by("field"))` — пагинация и сортировка
- `r.ft().aggregate(AggregateRequest(...))` — агрегация (count, sum, avg)

IndexType: `JSON` (для JSON-документов) или `HASH` (для Hash-ов).

Применение в AgentsSwarm:

- Поиск роботов по параметрам (модель, статус, зона)
- Фильтрация задач по приоритету и типу
- Агрегация метрик по различным измерениям

---

## Feature Store

### Назначение

Redis используется как online Feature Store для ML-инференса — хранилище агрегированных признаков с быстрым доступом (< 1 мс).

### Паттерн

- Hash-ы с TTL: `features:{robot_id}:latest` — последние вычисленные признаки
- TimeSeries: rolling window агрегаты (средняя скорость за 5 мин, max температура за 1 час)
- Pipelines для batch-обновления признаков перед каждым инференс-запросом

### Векторный поиск

Redis поддерживает хранение и поиск векторов (embeddings) через RediSearch:

- Хранение FLOAT32/FLOAT64 векторов в JSON или Hash
- Поиск ближайших соседей (KNN) для similarity search
- Применение: поиск похожих объектов/сцен, семантический поиск в истории событий

---

## Политики кэширования

| Тип данных | TTL | Паттерн |
|------------|-----|---------|
| Телеметрия (текущая) | 30s | Hash с setex, перезаписывается каждым новым значением |
| Состояние робота | 5m | Hash, обновляется при каждом изменении |
| Результат инференса | 1m–5m | String/Hash с setex |
| Конфигурация | Без TTL | Hash, инвалидация через Pub/Sub при изменении |
| Feature Store | 10s–60s | Hash/TimeSeries с retention |
| Метаданные задач | 30m | Hash, удаляется при завершении задачи |

Invalidation: Pub/Sub сообщения для инвалидации кэша при изменении данных в source-of-truth (PostgreSQL, InfluxDB).

---

## Best Practices

- Pipelines для любых batch-операций (> 2 команд) — 10x+ ускорение
- `transaction=True` для атомарных операций над связанными ключами
- Consumer Groups для распределённой обработки Streams — надёжный аналог RabbitMQ work queues
- xack обязателен для каждого обработанного сообщения — иначе оно остаётся в pending
- TimeSeries с labels для кросс-роботовых агрегатов: `ts.mget(["zone=warehouse"])` 
- `decode_responses=True` для всех клиентов — иначе все значения возвращаются как bytes
- async client (`redis.asyncio`) для интеграции в FastAPI / asyncio event loop
- Sentinel для production — автоматический failover
- Отдельный ConnectionPool при shared usage между несколькими клиентами
