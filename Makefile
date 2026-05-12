.PHONY: help clone submodule-init build up restart down clean logs ps

COMPOSE_FILE := ./docker/docker-compose.yml
PROJECT_NAME := control
REPO_URL := https://github.com/deneal123/AgentsSwarm.git
PROJECT_DIR := isaac_mission_control

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clone: ## Клонировать репозиторий с подмодулями
	git clone --recurse-submodules $(REPO_URL)
	@echo "Готово! Перейдите в папку: cd $(PROJECT_DIR)"

submodule-init: ## Подтянуть подмодуль
	git submodule update --init --recursive

up: ## Собрать и запустить в фоне
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) up --build -d

restart: ## Перезапустить
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) restart

down: ## Остановить
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down

clean: down ## Полная очистка
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down -v --rmi all

logs: ## Показать логи
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

ps: ## Статус контейнеров
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) ps

start: clone ## Полный цикл: клонировать и запустить
	cd $(PROJECT_DIR) && $(MAKE) up