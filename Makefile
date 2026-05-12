.PHONY: help submodule build up restart down logs ps shell clean first-start

PROJECT_NAME := workspace
COMPOSE_FILE := ./docker/docker-compose.ros2.yml
CONTAINER_NAME := vda5050_client

ROS_DISTRO ?= jazzy
UBUNTU_VERSION ?= 24.04

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

submodule: ## Инициализировать и обновить git submodules
	git submodule update --init --recursive

build: ## Собрать ROS workspace контейнер
	./build_ros.sh -d $(ROS_DISTRO) -v $(UBUNTU_VERSION)

first-start: submodule build ## Первый запуск: submodules + сборка workspace

up: ## Запустить контейнер в фоне
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) up -d

restart: down up ## Перезапустить контейнер

down: ## Остановить контейнер
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down

logs: ## Показать логи контейнеров
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

ps: ## Показать статус контейнеров
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) ps

shell: ## Войти в контейнер VDA5050 client
	docker exec -it $(CONTAINER_NAME) /bin/bash

clean: down ## Остановить контейнер и удалить volumes
	docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down -v