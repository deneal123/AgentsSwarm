# InfluxDB — Временные ряды

## Роль

InfluxDB 3.0 используется для хранения телеметрии роботов, метрик системных компонентов и событий со временем. Поддерживает агрегацию, downsampling и retention-политики. Взаимодействие осуществляется через Python-клиент **influxdb3-python** (модуль `influxdb_client_3`), который обеспечивает запись данных через HTTP и чтение через Apache Arrow Flight (gRPC).

---

## Клиент influxdb3-python

### Инициализация

Основной класс — `InfluxDBClient3`. При инициализации создаёт:

- **Write client** (singleton) — для записи данных в базу
- **Flight client** (singleton) — для выполнения SQL/InfluxQL запросов через gRPC

Параметры подключения:

- **host** — URL хоста InfluxDB
- **database** — имя базы данных (bucket)
- **token** — токен доступа с правами чтения/записи
- **write_client_options** (опционально) — настройки записи (синхронная или пакетная)
- **flight_client_options** (опционально) — настройки Flight-клиента (TLS-сертификаты)

Рекомендуется использовать контекстный менеджер (`with...as`) для корректного освобождения ресурсов: при выходе из блока отправляются все накопленные данные из батча и закрываются клиенты.

### Зависимости

- **pyarrow** — обязательная зависимость (устанавливается автоматически)
- **pandas** — опциональная (для to_pandas(), write_dataframe())
- **polars** — опциональная (для write_dataframe() с polars DataFrame)
- Python 3.9+ (рекомендуется 3.11+ для лучшей производительности)

---

## Дизайн измерений

### Line Protocol

InfluxDB использует формат Line Protocol для записи данных:

`measurement,tag_key=tag_value field_key=field_value timestamp`

### Структура данных в AgentsSwarm

- **measurement**: `robot_telemetry`, `system_metrics`, `inference_events`, `robot_events`
- **tags** (индексируемые метаданные): `robot_id`, `component`, `zone`, `tenant_id`, `model_name`
- **fields** (значения): `battery`, `speed`, `temperature`, `error_code`, `latency_ms`, `gpu_utilization`
- **timestamp**: unix epoch; точность настраивается через WritePrecision (`ns`, `us`, `ms`, `s`)

### Дополнительные measurements

| Measurement | Tags | Fields | Частота |
|-------------|------|--------|---------|
| `robot_telemetry` | robot_id, component, zone | battery, speed, temperature, position_x/y/z | 10–50 Гц |
| `system_metrics` | service_name, host, container_id | cpu_percent, memory_mb, gpu_util, gpu_memory_mb | 1–10 Гц |
| `inference_events` | model_name, robot_id, inference_type | latency_ms, confidence, tokens_per_sec | По событию |
| `robot_events` | robot_id, event_type, severity | duration_ms, error_code | По событию |
| `mqtt_metrics` | broker_node, topic_pattern | messages_per_sec, connected_clients, bytes_received | 1 Гц |

---

## Режимы записи

### Синхронная запись (по умолчанию)

Если при инициализации клиента не указаны write_client_options, запись происходит синхронно: клиент немедленно отправляет данные в InfluxDB, не выполняет повторных попыток при ошибках и не вызывает callbacks. Подходит для единичных записей или отладки. Режим можно указать явно через `write_options=SYNCHRONOUS`.

### Пакетная запись (Batch Writing)

Рекомендуемый режим для продакшена. Клиент группирует записи в пакеты и отправляет их по достижении порога batch_size или по истечении flush_interval. При ошибке автоматически повторяет отправку.

Настройка через класс **WriteOptions**:

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| batch_size | 1000 | Количество записей в одном батче |
| flush_interval | 1000 мс | Интервал автоматической отправки батча |
| jitter_interval | 0 мс | Случайная задержка для распределения нагрузки |
| retry_interval | 5000 мс | Начальный интервал между повторными попытками |
| max_retries | 5 | Максимальное количество повторных попыток |
| max_retry_delay | 125000 мс | Максимальная задержка между повторами |
| max_retry_time | 180000 мс | Общее время на все повторные попытки |
| exponential_base | 2 | База для экспоненциального backoff |
| max_close_wait | 300000 мс | Максимальное время ожидания при закрытии клиента |

### Callbacks для пакетной записи

При использовании пакетного режима можно назначить callback-функции через `write_client_options`:

- **success_callback** — вызывается после успешной записи батча (HTTP 204)
- **error_callback** — вызывается при ошибке записи (не-204 ответ)
- **retry_callback** — вызывается при повторной попытке отправки

Callbacks позволяют реализовать мониторинг, логирование и алертинг на уровне приложения.

---

## Форматы записи

### Point (рекомендуемый)

Класс `Point` предоставляет fluent-интерфейс для конструирования точки данных:

- `Point("measurement")` — создание точки для заданного measurement
- `.tag("key", "value")` — добавление тега
- `.field("key", value)` — добавление поля
- Результат передаётся в `client.write(point)`

Также доступен контроль порядка тегов для оптимизации первичной записи (InfluxDB 3 Enterprise) через параметр `tag_order` в WriteOptions.

### Line Protocol строка

Прямая запись строки в формате Line Protocol: `"measurement fieldname=value timestamp"`.

### Словарь (dict)

Клиент сериализует Python-словарь с ключами: `measurement`, `tags` (dict), `fields` (dict), `time`.

### DataFrame (Pandas / Polars)

Метод `write_dataframe()` принимает Pandas или Polars DataFrame с обязательными параметрами:

- **measurement** — имя measurement
- **timestamp_column** — имя столбца с временными метками
- **tags** — список имён столбцов, интерпретируемых как теги

Остальные столбцы автоматически становятся fields.

### Запись из файлов

Метод `write_file()` поддерживает импорт данных из:

- **CSV** (.csv)
- **JSON** (.json)
- **Feather** (.feather) — Apache Arrow columnar format
- **Parquet** (.parquet)
- **ORC** (.orc)

Параметры: `file` (путь), `timestamp_column`, `tag_columns` (список), `measurement_name`, `write_precision`.

---

## Запросы (Query)

### Протокол

Запросы выполняются через **Apache Arrow Flight** (gRPC). Клиент оборачивает `pyarrow.flight.FlightStreamReader` в удобный интерфейс. Поддерживаются два языка запросов:

- **SQL** (по умолчанию) — полноценный SQL с поддержкой INTERVAL, функций агрегации, JOIN
- **InfluxQL** — legacy-совместимый язык запросов InfluxDB

### Режимы получения результатов (mode)

| Режим | Возвращаемый тип | Описание |
|-------|------------------|----------|
| `all` (default) | `pyarrow.Table` | Полное содержимое потока в виде Arrow Table |
| `chunk` | FlightStreamChunk | Следующий чанк данных (для потоковой обработки) |
| `pandas` | `pandas.DataFrame` | Автоматическая конвертация в pandas DataFrame |
| `reader` | `pyarrow.RecordBatchReader` | Итератор по Record Batches |
| `schema` | Schema | Схема результата без данных |

Альтернативно: метод `query_dataframe()` возвращает DataFrame напрямую с поддержкой Pandas и Polars через параметр `frame_type`.

### Timeout

Для длительных запросов можно задать timeout в секундах через параметр `timeout` метода query.

### gRPC компрессия

- **Ответы**: компрессия включена по умолчанию (gzip). Клиент отправляет заголовок `grpc-accept-encoding: identity, deflate, gzip`, сервер возвращает сжатые ответы. Декомпрессия автоматическая
- **Запросы**: компрессия запросов не поддерживается InfluxDB 3
- Компрессию ответов можно отключить через параметр `disable_grpc_compression=True` или переменную окружения `INFLUX_DISABLE_GRPC_COMPRESSION=true`

---

## Retention и downsampling

- **Горячие данные**: retention 7 дней с full resolution (все точки)
- **Среднесрочные**: агрегаты (1m, 5m) — retention 30 дней
- **Долгосрочные**: агрегаты (1h) — retention 1 год

Downsampling реализуется через Continuous Queries или внешние Celery-задачи, агрегирующие данные по расписанию.

---

## Интеграция в AgentsSwarm

- **Collector**: Telegraf + Prometheus exporters для системных метрик; прямая запись через influxdb3-python из Edge AI Proxy и MQTT Bridge
- **Grafana дашборды**: прямое подключение к InfluxDB через Flight SQL; готовые дашборды для состояния роботов, GPU-утилизации, латентности инференса
- **ETL**: Celery-задачи для downsampling и экспорта агрегатов в PostgreSQL для репортинга
- **ML Pipeline**: экспорт временных рядов в pandas/polars DataFrame для анализа и обучения моделей
- **TLS**: настройка Flight client options с указанием корневых сертификатов для безопасного подключения
- **WritePrecision**: `s` (секунды) для системных метрик, `ms` (миллисекунды) для телеметрии роботов, `us` / `ns` для высокоточных измерений

---

## Best Practices

- Использовать пакетную запись с WriteOptions для продакшена: batch_size=500–1000, flush_interval=10000
- Всегда указывать write_precision явно для консистентности временных меток
- Теги — для фильтрации (robot_id, zone); поля — для значений (temperature, speed). Теги индексируются, поля — нет
- Контекстный менеджер (`with...as`) для гарантированной отправки буферов при завершении
- Callbacks для мониторинга: логировать error_callback и retry_callback
- Для массового импорта исторических данных: write_file() с CSV/Parquet
- query с mode="pandas" для прямого получения DataFrame без промежуточных преобразований
