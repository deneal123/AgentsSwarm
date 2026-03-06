# MinIO — Объектное хранилище

## Роль

MinIO используется как S3-совместимое объектное хранилище для бинарных данных: весов моделей, датасетов обучения, видеозаписей, логов ROS 2 (rosbag), карт и snapshots. Взаимодействие через Python-клиент **minio-py** (`from minio import Minio`).

---

## Клиент minio-py

### Инициализация

`Minio(endpoint, access_key, secret_key, ...)` — создание клиента.

Параметры конструктора:

| Параметр | Тип | Описание |
|----------|-----|----------|
| `endpoint` | str | URL сервера (без `http://`, напр. `play.min.io:443`) |
| `access_key` | str | Ключ доступа (аналог AWS Access Key ID) |
| `secret_key` | str | Секретный ключ (аналог AWS Secret Access Key) |
| `secure` | bool | HTTPS (True по умолчанию) |
| `region` | str | Регион по умолчанию для новых бакетов |
| `http_client` | urllib3.PoolManager | Пользовательский HTTP-клиент (для proxy, кастомных CA сертификатов) |
| `credentials` | Provider | Кастомный провайдер аутентификации (IAM, STS, ENV-based) |
| `cert_check` | bool | Проверка SSL-сертификатов (True по умолчанию) |

### Потокобезопасность

- **threading** — безопасно (можно использовать один клиент из нескольких потоков)
- **multiprocessing** — НЕ безопасно (необходимо создавать отдельный клиент в каждом дочернем процессе)

---

## Управление бакетами

### Создание

`make_bucket(bucket_name)` — создать бакет.

- `make_bucket(bucket_name, location="eu-west-1")` — с указанием региона
- `make_bucket(bucket_name, object_lock=True)` — с поддержкой Object Lock (WORM-защита, требует versioning)

### Перечисление и проверка

- `list_buckets()` — список всех бакетов (возвращает объекты Bucket с полями `name`, `creation_date`)
- `bucket_exists(bucket_name)` — проверка существования бакета (возвращает bool)

### Удаление

`remove_bucket(bucket_name)` — удалить пустой бакет. Перед удалением необходимо очистить все объекты и незавершённые multipart-загрузки.

### Листинг объектов

`list_objects(bucket_name, ...)` — итерация по объектам в бакете:

- `prefix=""` — фильтр по префиксу (имитация директорий)
- `recursive=False` — рекурсивный обход (True) или только текущий "уровень" (False)
- `start_after=""` — листинг после указанного ключа (для пагинации)
- С включённым versioning — возвращает все версии каждого объекта (поле `version_id`)

Каждый Object содержит: `object_name`, `size`, `etag`, `last_modified`, `is_dir`, `version_id`.

---

## Политики и уведомления

### Bucket Policy (IAM)

`set_bucket_policy(bucket_name, policy_json)` — установить IAM-стиль JSON-политику доступа к бакету. Формат совместим с AWS S3 Bucket Policy.

`get_bucket_policy(bucket_name)` — получить текущую политику.

### Уведомления (Event Notifications)

`listen_bucket_notification(bucket_name, prefix="", suffix="", events=["s3:ObjectCreated:*"])` — подписка на события бакета. Возвращает генератор событий.

Типы событий:

- `s3:ObjectCreated:*` — создание/загрузка объекта
- `s3:ObjectRemoved:*` — удаление
- `s3:ObjectAccessed:*` — доступ

Применение в AgentsSwarm: автоматический триггер при загрузке новой модели — Triton Inference Server получает уведомление и перезагружает модель.

---

## Шифрование

MinIO поддерживает три метода шифрования на стороне сервера (Server-Side Encryption):

| Метод | Описание | Управление ключами |
|-------|----------|-------------------|
| **SSE-S3** | Шифрование управляемым ключом сервера | MinIO |
| **SSE-KMS** | Шифрование через Key Management Service | KMS (Vault, AWS KMS) |
| **SSE-C** | Шифрование пользовательским ключом (ключ передаётся в каждом запросе) | Клиент |

SSE-C: при каждом get/put-запросе клиент передаёт ключ шифрования. MinIO не хранит ключ — при потере ключа данные теряются навсегда.

---

## Versioning и Lifecycle

### Versioning

`set_bucket_versioning(bucket_name, VersioningConfig("Enabled"))` — включить версионирование. Каждая перезапись создаёт новую версию, старые версии доступны по `version_id`.

### Lifecycle Rules

`set_bucket_lifecycle(bucket_name, LifecycleConfig([rules]))` — установить правила жизненного цикла:

- **Transition** — перенос на другой Storage Class (напр. с SSD на HDD / GLACIER)
- **Expiration** — автоматическое удаление объектов через N дней
- **NoncurrentVersionExpiration** — удаление старых версий через N дней

Применение в AgentsSwarm:

- Логи rosbag: хранение 30 дней на SSD, затем переход на HDD, удаление через 180 дней
- Датасеты обучения: версионирование для воспроизводимости экспериментов
- Снапшоты моделей: хранение 5 последних версий, автоудаление старых

### Replication

`set_bucket_replication(bucket_name, ReplicationConfig(...))` — настройка кросс-кластерной репликации бакетов для DR (disaster recovery).

---

## Object Lock (WORM)

Защита объектов от удаления и перезаписи:

- `GOVERNANCE` — привилегированные пользователи могут снять блокировку
- `COMPLIANCE` — блокировка не может быть снята никем до истечения срока
- `Legal Hold` — отдельный флаг блокировки, не зависит от retention

Применение: audit-логи, нормативно-значимые данные.

---

## Операции с объектами

### Загрузка (Upload)

`put_object(bucket_name, object_name, data, length, ...)` — загрузка из потока:

- `data` — любой объект с методом `read()` (файловый объект, BytesIO)
- `length` — размер данных в байтах
- `content_type` — MIME-тип (напр. `"application/octet-stream"`)
- `metadata` — произвольные метаданные (dict)
- `sse` — шифрование (SSE-S3/SSE-KMS/SSE-C)
- `tags` — теги объекта (Tags)
- `retention` — настройки Object Lock retention
- `progress` — callback для отслеживания прогресса загрузки

`fput_object(bucket_name, object_name, file_path, ...)` — загрузка из файла на диске. Content-type определяется автоматически по расширению файла.

### Скачивание (Download)

`get_object(bucket_name, object_name, ...)` — скачивание как HTTP response:

- `offset` и `length` — частичное скачивание (Range request)
- `version_id` — конкретная версия объекта
- Ответ — объект `urllib3.HTTPResponse`, обязательно вызвать `close()` и `release_conn()` после чтения

`fget_object(bucket_name, object_name, file_path, ...)` — скачивание в файл на диске.

### Копирование (серверное)

`copy_object(bucket_name, object_name, CopySource(...))` — серверное копирование (данные не передаются через клиент):

- Максимальный размер — 5 ГБ
- `CopySource(bucket, object, version_id, conditions)` — условное копирование (if-modified-since, if-match etag)
- Для объектов > 5 ГБ используется `compose_object()`

### Композиция

`compose_object(bucket_name, object_name, [ComposeSource(...), ...])` — объединение нескольких объектов в один на стороне сервера. Каждый ComposeSource — отдельный объект (или его часть с offset/length).

### Метаданные

`stat_object(bucket_name, object_name)` — получить метаданные объекта без скачивания тела: размер, etag, content_type, last_modified, metadata, version_id.

### Удаление

- `remove_object(bucket_name, object_name)` — удалить один объект
- `remove_objects(bucket_name, [DeleteObject(name), ...])` — batch-удаление (возвращает итератор ошибок)

### Теги

- `set_object_tags(bucket_name, object_name, Tags({"env": "prod"}))` — установить теги
- `get_object_tags(bucket_name, object_name)` — получить теги

---

## Presigned URLs

Генерация временных подписанных URL для доступа к объектам без аутентификации:

- `presigned_get_object(bucket_name, object_name, expires=timedelta(days=7))` — URL для скачивания
- `presigned_put_object(bucket_name, object_name, expires=timedelta(days=7))` — URL для загрузки
- `get_presigned_url("GET"/"PUT", bucket_name, object_name, expires)` — универсальный метод
- `presigned_post_policy(PostPolicy)` — POST-форма для загрузки через браузер с условиями (max size, content-type, key prefix)
- Срок по умолчанию — 7 дней, максимум — 7 дней

Применение в AgentsSwarm:

- Dashboard UI: presigned GET для отображения видеозаписей и карт
- Загрузка rosbag: presigned PUT URL передаётся Edge-агенту для прямой загрузки
- Обмен моделями: временные ссылки на веса для скачивания на Edge-устройства

---

## S3 Select

`select_object_content(bucket_name, object_name, SelectRequest(...))` — выполнение SQL-запросов непосредственно на CSV/JSON файлах в MinIO без полного скачивания. Возвращает только отфильтрованные данные — экономия сетевого трафика.

Поддерживаемые форматы: CSV, JSON.

---

## Специальные операции

### Snowball Upload

`upload_snowball_objects(bucket_name, [SnowballObject(name, data, length)])` — загрузка множества мелких объектов в одном TAR-архиве. MinIO автоматически распаковывает и сохраняет как отдельные объекты. Эффективнее чем множество отдельных put_object для большого количества мелких файлов.

### Append Object

`append_object(bucket_name, object_name, data, length, headers)` — дозапись данных в существующий объект. Полезно для потоковых логов.

---

## Организация хранилища в AgentsSwarm

### Структура бакетов

| Бакет | Содержимое | Versioning | Lifecycle |
|-------|-----------|------------|-----------|
| `models` | Веса моделей (Triton, vLLM, SmolVLA) | Да | Хранение 5 последних версий |
| `datasets` | Датасеты обучения и fine-tuning | Да | Без ограничений |
| `rosbags` | Логи ROS 2 (rosbag2) | Нет | 30 дней SSD → HDD → 180 дней удаление |
| `videos` | Видеозаписи камер роботов | Нет | 7 дней |
| `maps` | Карты среды (SLAM, occupancy grids) | Да | Без ограничений |
| `snapshots` | Снапшоты состояния системы | Нет | 30 дней |
| `audit-logs` | Аудит-логи | Object Lock (COMPLIANCE) | 365 дней |

### Naming Convention

Формат ключей объектов: `{category}/{date}/{robot_id}/{filename}`.

Примеры:

- `rosbags/2025-01-15/robot-arm-01/session_1421.mcap`
- `models/smolvla/v2.3/weights.safetensors`
- `videos/2025-01-15/robot-arm-01/camera_front_1421.mp4`

### Интеграция с Event Notifications

Бакет `models` настроен с event notification: при `s3:ObjectCreated:Put` — отправка сообщения в RabbitMQ, которое триггерит перезагрузку модели на Triton Inference Server.

---

## Best Practices

- Presigned URLs для прямого доступа Edge-устройств — снижение нагрузки на Gateway
- Snowball upload для массовой загрузки мелких файлов (логи, снапшоты)
- Versioning для моделей и датасетов — воспроизводимость экспериментов
- Lifecycle rules для автоматической ротации логов и видео
- Object Lock (COMPLIANCE) для аудит-логов — соответствие нормативным требованиям
- Отдельный клиент на каждый процесс при использовании multiprocessing
- SSE-S3 шифрование для чувствительных данных (модели, конфигурации)
- Event Notifications → RabbitMQ для event-driven обновления моделей
- Metadata и Tags для классификации объектов и интеграции с RediSearch
