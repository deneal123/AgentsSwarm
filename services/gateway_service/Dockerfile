# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Poetry
ENV POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /app

# Копируем только lock-файлы (кэш слоя)
COPY pyproject.toml poetry.lock* ./

# Устанавливаем зависимости без dev-группы
RUN poetry install --only=main --no-root --no-ansi

# Копируем исходный код
COPY src/ ./src/

# Устанавливаем пакет
RUN poetry install --only=main --no-ansi

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Минимальные runtime-зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser

WORKDIR /app

# Копируем venv из builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src

# Активируем virtualenv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src"

# Непривилегированный пользователь
USER appuser

EXPOSE 8005

# Healthcheck: liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "gateway_service.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8005", \
    "--workers", "1", \
    "--loop", "uvloop", \
    "--http", "httptools", \
    "--access-log"]
