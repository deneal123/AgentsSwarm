.PHONY: help env up restart down clean prune logs logs-web logs-sim ps shell

COMPOSE_FILE := ./IsaacSim/tools/docker/docker-compose.yml
PROJECT_NAME := isim
ENV_FILE := ./IsaacSim/tools/docker/.env

ISAAC_SIM_IMAGE ?= nvcr.io/nvidia/isaac-sim:6.0.0-dev2
ISAAC_SIM_DATA ?= /root/docker/isaac-sim

ISAACSIM_HOST ?= 195.225.110.91
ISAACSIM_SIGNAL_PORT ?= 49100
ISAACSIM_STREAM_PORT ?= 47998

WEB_VIEWER_PORT ?= 8210
GPU_DEVICE ?= all

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

env: ## Создать .env файл в tools/docker/.env
	@mkdir -p tools/docker
	@cat > $(ENV_FILE) << EOF
# ============================================================================
# Docker Compose environment variables for Isaac Sim + Web Viewer
# ============================================================================

# --- Isaac Sim Image ---
# Use a prebuilt NGC image instead of the locally built isaac-sim-docker:latest.
# This skips the local build steps.
ISAAC_SIM_IMAGE=$(ISAAC_SIM_IMAGE)

# --- Persistent Data ---
# Host path for cache, config, logs, and data.
# Use a full absolute path; ~ is not expanded by Docker Compose.
ISAAC_SIM_DATA=$(ISAAC_SIM_DATA)

# --- WebRTC Streaming ---
# Host IP for Isaac Sim WebRTC streaming.
# Set this to your machine's LAN/public IP when connecting from another device.
# The web viewer bakes this at build time, so use --build when changing it.
ISAACSIM_HOST=$(ISAACSIM_HOST)

# Signal port for WebRTC signaling (TCP).
ISAACSIM_SIGNAL_PORT=$(ISAACSIM_SIGNAL_PORT)

# Media port for WebRTC stream (UDP).
ISAACSIM_STREAM_PORT=$(ISAACSIM_STREAM_PORT)

# --- Web Viewer ---
# Port the web viewer listens on.
WEB_VIEWER_PORT=$(WEB_VIEWER_PORT)

# --- GPU ---
# GPU index to pin Isaac Sim to.
# Default is "all" — use all available GPUs.
GPU_DEVICE=$(GPU_DEVICE)
EOF
	@echo ".env файл создан: $(ENV_FILE)"

up: env ## Собрать и запустить Isaac Sim в фоне
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) up --build -d

restart: ## Перезапустить контейнеры
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) restart

down: ## Остановить контейнеры
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down

clean: ## Остановить контейнеры и удалить volumes
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down -v

prune: clean ## Очистить Docker build cache и неиспользуемые volumes
	docker builder prune -a -f
	docker volume prune -f

logs: ## Показать все логи
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

logs-web: ## Показать логи web-viewer
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f web-viewer

logs-sim: ## Показать логи isaac-sim
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f isaac-sim

ps: ## Показать статус контейнеров
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) ps

shell: ## Открыть shell внутри контейнера isaac-sim
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) exec isaac-sim bash