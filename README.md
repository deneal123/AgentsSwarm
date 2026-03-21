# vLLM Service

OpenAI-совместимый сервер для инференса LLM-моделей с поддержкой Data Parallel на базе vLLM.

## Возможности

- 🚀 **OpenAI-совместимый API**: полная совместимость с OpenAI Chat Completions, Completions и Embeddings API
- 🔄 **Data Parallel**: распределённый инференс на нескольких GPU/нодах
- ⚡ **Высокая производительность**: оптимизации vLLM для максимальной пропускной способности
- 🐳 **Docker-ready**: готовые Docker-образы и docker-compose конфигурации

## Быстрый старт

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd vllm_service

# Установка зависимостей
pip install poetry
poetry install

# Активация виртуального окружения
poetry shell
```

### Запуск (одна нода)

```bash
# Через CLI
vllm-service serve --model Qwen/Qwen2.5-7B-Instruct

# Или через Python
python -m vllm_service serve --model Qwen/Qwen2.5-7B-Instruct
```

### Запуск через Docker

#### Одна нода (без Data Parallel)

```bash
cd docker
cp .env.node0 .env
# Оставьте VLLM_DATA_PARALLEL_SIZE=1
./deploy.sh build
./deploy.sh up
```

#### Data Parallel (2 ноды на разных серверах)

**Нода 0 (Coordinator)** - на первом сервере:
```bash
cd docker
cp .env.node0 .env
# Отредактируйте .env: укажите IP этого сервера в VLLM_DATA_PARALLEL_ADDRESS
./deploy.sh build
./deploy.sh up
```

**Нода 1 (Worker)** - на втором сервере:
```bash
cd docker
cp .env.node1 .env
# Отредактируйте .env: укажите IP первого сервера в VLLM_DATA_PARALLEL_ADDRESS
./deploy.sh build
./deploy.sh up
```

#### Проверка статуса

```bash
./deploy.sh status
curl http://localhost:8000/health
```

## Data Parallel Deployment

Для развертывания на нескольких нодах (например, 2 GPU V100 по 32GB каждая):

### Конфигурация переменных окружения

#### Нода 0 (Coordinator, rank 0)

```bash
# .env для ноды 0
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_MODEL_DTYPE=auto
VLLM_MAX_MODEL_LEN=4096
VLLM_GPU_MEMORY_UTILIZATION=0.9

VLLM_HOST=0.0.0.0
VLLM_PORT=8000
VLLM_API_KEY=your-api-key

VLLM_DATA_PARALLEL_SIZE=2
VLLM_DATA_PARALLEL_RANK=0
VLLM_DATA_PARALLEL_ADDRESS=10.0.0.1  # IP ноды 0
VLLM_DATA_PARALLEL_RPC_PORT=13345
VLLM_DATA_PARALLEL_SIZE_LOCAL=1
```

#### Нода 1 (Worker, rank 1)

```bash
# .env для ноды 1
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_MODEL_DTYPE=auto
VLLM_MAX_MODEL_LEN=4096
VLLM_GPU_MEMORY_UTILIZATION=0.9

VLLM_HOST=0.0.0.0
VLLM_PORT=8000
VLLM_API_KEY=your-api-key

VLLM_DATA_PARALLEL_SIZE=2
VLLM_DATA_PARALLEL_RANK=1
VLLM_DATA_PARALLEL_ADDRESS=10.0.0.1  # IP ноды 0 (coordinator)
VLLM_DATA_PARALLEL_RPC_PORT=13345
VLLM_DATA_PARALLEL_SIZE_LOCAL=1
```

### Запуск Data Parallel кластера

```bash
# На ноде 0 (сначала!)
vllm-service serve \
    --model Qwen/Qwen2.5-7B-Instruct \
    --data-parallel-size 2 \
    --data-parallel-rank 0 \
    --data-parallel-address 10.0.0.1

# На ноде 1 (после запуска ноды 0)
vllm-service serve \
    --model Qwen/Qwen2.5-7B-Instruct \
    --data-parallel-size 2 \
    --data-parallel-rank 1 \
    --data-parallel-address 10.0.0.1 \
    --headless
```

### Docker Compose для Data Parallel

```bash
# На каждом сервере:
cd docker

# Скопируйте нужный .env файл
cp .env.node0 .env  # для ноды 0 (coordinator)
# или
cp .env.node1 .env  # для ноды 1 (worker)

# Отредактируйте .env:
# - VLLM_DATA_PARALLEL_ADDRESS = IP ноды 0
# - VLLM_API_KEY = ваш API ключ

# Запустите
./deploy.sh build
./deploy.sh up
```

### Скрипты деплоя

```bash
cd docker

# Linux/macOS
./deploy.sh build    # Собрать образ
./deploy.sh up       # Запустить сервис
./deploy.sh down     # Остановить сервис
./deploy.sh logs     # Логи
./deploy.sh status   # Статус

# Windows
deploy.bat build
deploy.bat up
deploy.bat down
deploy.bat logs
deploy.bat status
```

## Использование API

### Chat Completions

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    temperature=0.7,
    max_tokens=100,
)

print(response.choices[0].message.content)
```

### Streaming

```python
stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### vLLM-специфичные параметры

```python
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "Hello"}],
    extra_body={
        "top_k": 50,
        "repetition_penalty": 1.2,
        "min_tokens": 10,
    }
)
```

## API Endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /v1/models` | Список доступных моделей |
| `GET /v1/models/{model_id}` | Информация о модели |
| `POST /v1/chat/completions` | Chat completions |
| `POST /v1/completions` | Text completions |
| `POST /v1/embeddings` | Эмбеддинги |
| `POST /tokenize` | Токенизация текста |
| `POST /detokenize` | Детокенизация |
| `GET /health` | Health check |
| `GET /ready` | Readiness check |

## Конфигурация

Все параметры можно задать через переменные окружения (префикс `VLLM_`) или в `settings.toml`.

### Основные параметры

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `VLLM_MODEL_NAME` | Имя или путь к модели | - |
| `VLLM_MODEL_DTYPE` | Тип данных (auto, float16, bfloat16) | auto |
| `VLLM_MAX_MODEL_LEN` | Максимальная длина контекста | 4096 |
| `VLLM_GPU_MEMORY_UTILIZATION` | Использование GPU памяти (0-1) | 0.9 |
| `VLLM_HOST` | Хост сервера | 0.0.0.0 |
| `VLLM_PORT` | Порт сервера | 8000 |
| `VLLM_API_KEY` | API ключ для аутентификации | - |

### Data Parallel параметры

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `VLLM_DATA_PARALLEL_SIZE` | Общее количество DP рангов | 1 |
| `VLLM_DATA_PARALLEL_RANK` | Ранг текущей ноды | 0 |
| `VLLM_DATA_PARALLEL_ADDRESS` | Адрес coordinator (rank 0) | localhost |
| `VLLM_DATA_PARALLEL_RPC_PORT` | RPC порт для координации | 13345 |
| `VLLM_DATA_PARALLEL_SIZE_LOCAL` | Локальных рангов на ноде | 1 |

## Разработка

### Установка для разработки

```bash
poetry install --with dev

# Установка pre-commit хуков
poetry run pre-commit install
```

### Запуск тестов

```bash
# Все тесты
poetry run pytest tests/ -v

# С покрытием
poetry run pytest tests/ --cov=src/vllm_service --cov-report=html
```

### Форматирование

```bash
poetry run black src/ tests/
poetry run isort src/ tests/
```

## Требования

- Python 3.12
- CUDA 12.1+
- GPU с поддержкой CUDA (рекомендуется 16GB+ VRAM)

## Лицензия

MIT