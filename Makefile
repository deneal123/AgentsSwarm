# =============================================================================
# AgentsSwarm — Makefile
# =============================================================================

.PHONY: help up down build logs ps clean test lint migrate seed \
        up-infra up-app up-gpu up-monitoring health proto

COMPOSE        := docker compose
COMPOSE_DEV    := $(COMPOSE) -f docker-compose.dev.yml
COMPOSE_PROD   := $(COMPOSE) -f docker-compose.yml
COMPOSE_GPU    := $(COMPOSE_DEV) --profile gpu
COMPOSE_MON    := $(COMPOSE_DEV) --profile monitoring

SERVICES       := gateway_service orchestrator vllm_service triton_inference \
                  smolvla_service communication_service robot_edge frontend

# ─── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AgentsSwarm — управление проектом"
	@echo ""
	@echo "  Основные команды:"
	@echo "    make up            — запустить все сервисы (dev)"
	@echo "    make down          — остановить все сервисы"
	@echo "    make build         — собрать все Docker-образы"
	@echo "    make logs          — показать логи (все сервисы)"
	@echo "    make ps            — статус контейнеров"
	@echo "    make clean         — удалить контейнеры и volumes"
	@echo ""
	@echo "  Профили:"
	@echo "    make up-infra      — только БД и брокеры"
	@echo "    make up-app        — инфраструктура + application-сервисы"
	@echo "    make up-gpu        — + AI-сервисы (требует nvidia-container-toolkit)"
	@echo "    make up-monitoring — + Prometheus, Grafana, Jaeger"
	@echo ""
	@echo "  Dev-инструменты:"
	@echo "    make test          — запустить все тесты"
	@echo "    make lint          — запустить линтеры (ruff, mypy, eslint)"
	@echo "    make migrate       — применить Alembic-миграции"
	@echo "    make seed          — загрузить тестовые данные"
	@echo "    make health        — проверить состояние всех сервисов"
	@echo "    make proto         — сгенерировать код из .proto файлов (через buf)"
	@echo "    make proto-local   — сгенерировать через grpcio-tools (без buf registry)"
	@echo ""

# ─── Запуск ───────────────────────────────────────────────────────────────────
up:
	$(COMPOSE_DEV) up -d
	@echo "✅  Все сервисы запущены. Дашборды:"
	@echo "    Frontend:      http://localhost:3000"
	@echo "    API Gateway:   http://localhost:8005/docs"
	@echo "    RabbitMQ UI:   http://localhost:15672"
	@echo "    EMQX Dashboard:http://localhost:18083"
	@echo "    MinIO Console: http://localhost:9001"
	@echo "    Neo4j Browser: http://localhost:7474"
	@echo "    InfluxDB UI:   http://localhost:8086"
	@echo "    Redis Insight: http://localhost:8001"

up-infra:
	$(COMPOSE_DEV) up -d postgres influxdb neo4j redis minio emqx rabbitmq

up-app: up-infra
	$(COMPOSE_DEV) up -d gateway orchestrator celery-worker communication-service frontend

up-gpu:
	$(COMPOSE_GPU) up -d

up-monitoring:
	$(COMPOSE_MON) up -d

down:
	$(COMPOSE_DEV) down

# ─── Сборка ───────────────────────────────────────────────────────────────────
build:
	./build.sh

build-service:
	@if [ -z "$(SERVICE)" ]; then echo "Укажите SERVICE=<name>"; exit 1; fi
	./build.sh --service $(SERVICE)

# ─── Логи и статус ────────────────────────────────────────────────────────────
logs:
	$(COMPOSE_DEV) logs -f

logs-service:
	@if [ -z "$(SERVICE)" ]; then echo "Укажите SERVICE=<name>"; exit 1; fi
	$(COMPOSE_DEV) logs -f $(SERVICE)

ps:
	$(COMPOSE_DEV) ps

# ─── Очистка ──────────────────────────────────────────────────────────────────
clean:
	$(COMPOSE_DEV) down -v --remove-orphans
	@echo "🧹  Контейнеры и volumes удалены."

clean-images:
	docker rmi $$(docker images "agentsswarm/*" -q) 2>/dev/null || true
	@echo "🧹  Образы AgentsSwarm удалены."

# ─── Тесты ────────────────────────────────────────────────────────────────────
test:
	@for svc in $(SERVICES); do \
	    if [ -d "services/$$svc" ]; then \
	        echo "▶  Testing $$svc..."; \
	        docker compose -f docker-compose.dev.yml run --rm $$svc \
	            pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80; \
	    fi \
	done

test-service:
	@if [ -z "$(SERVICE)" ]; then echo "Укажите SERVICE=<name>"; exit 1; fi
	$(COMPOSE_DEV) run --rm $(SERVICE) pytest tests/ -v --cov=src --cov-report=term-missing

# ─── Линтинг ──────────────────────────────────────────────────────────────────
lint:
	@echo "▶  Ruff (Python)..."
	@for svc in gateway_service orchestrator vllm_service triton_inference smolvla_service communication_service robot_edge; do \
	    if [ -d "services/$$svc" ]; then \
	        docker compose -f docker-compose.dev.yml run --rm $$svc ruff check src/ tests/; \
	        docker compose -f docker-compose.dev.yml run --rm $$svc mypy src/; \
	    fi \
	done
	@echo "▶  ESLint (Frontend)..."
	@if [ -d "services/frontend" ]; then \
	    docker compose -f docker-compose.dev.yml run --rm frontend npm run lint; \
	    docker compose -f docker-compose.dev.yml run --rm frontend npx tsc --noEmit; \
	fi
	@echo "✅  Lint завершён."

# ─── Миграции ─────────────────────────────────────────────────────────────────
migrate:
	$(COMPOSE_DEV) run --rm orchestrator alembic upgrade head
	@echo "✅  Миграции применены."

migrate-create:
	@if [ -z "$(MSG)" ]; then echo "Укажите MSG=<message>"; exit 1; fi
	$(COMPOSE_DEV) run --rm orchestrator alembic revision --autogenerate -m "$(MSG)"

migrate-downgrade:
	$(COMPOSE_DEV) run --rm orchestrator alembic downgrade -1

# ─── Тестовые данные ──────────────────────────────────────────────────────────
seed:
	./infrastructure/scripts/seed-data.sh
	@echo "✅  Тестовые данные загружены."

# ─── Инициализация БД ─────────────────────────────────────────────────────────
init-db:
	./infrastructure/scripts/init-db.sh
	@echo "✅  БД инициализированы."

# ─── Health check ─────────────────────────────────────────────────────────────
health:
	./infrastructure/scripts/health-check.sh

# ─── Protobuf ─────────────────────────────────────────────────────────────────
proto:
	@command -v buf >/dev/null 2>&1 || { echo "❌  buf не найден. Используйте: make proto-local"; exit 1; }
	cd proto && buf generate
	@echo "✅  Protobuf-код сгенерирован (buf)."

proto-local:
	@bash proto/scripts/gen-proto.sh
	@echo "✅  Protobuf-код сгенерирован (grpcio-tools)."

proto-lint:
	@command -v buf >/dev/null 2>&1 || { echo "❌  buf не найден"; exit 1; }
	cd proto && buf lint

proto-breaking:
	@command -v buf >/dev/null 2>&1 || { echo "❌  buf не найден"; exit 1; }
	cd proto && buf breaking --against '.git#branch=main'

# ─── Резервные копии ──────────────────────────────────────────────────────────
backup:
	./infrastructure/scripts/backup.sh

restore:
	@if [ -z "$(DATE)" ]; then echo "Укажите DATE=YYYY-MM-DD"; exit 1; fi
	./infrastructure/scripts/restore.sh $(DATE)

# ─── Утилиты ──────────────────────────────────────────────────────────────────
shell:
	@if [ -z "$(SERVICE)" ]; then echo "Укажите SERVICE=<name>"; exit 1; fi
	$(COMPOSE_DEV) exec $(SERVICE) bash

restart:
	@if [ -z "$(SERVICE)" ]; then \
	    $(COMPOSE_DEV) restart; \
	else \
	    $(COMPOSE_DEV) restart $(SERVICE); \
	fi
