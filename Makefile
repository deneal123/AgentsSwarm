SHELL := /bin/bash

ENV_FILE ?= .env
DOCKER_DIR := docker
COMPOSE_HEADLESS := $(DOCKER_DIR)/isaac.headless.yml
COMPOSE_GUI := $(DOCKER_DIR)/isaac.gui.yml
COMPOSE := docker compose

# Локальная папка с кешами/конфигами (используется скриптом и compose)
ISAAC_ROOT ?= ./tmp

.PHONY: help env prepare-root headless gui stop-headless stop-gui logs-headless logs-gui check script-headless script-gui clean

help:
	@echo "Available targets:"
	@echo "  env             - создать .env из .env.example (без перезаписи)"
	@echo "  headless        - запустить Isaac Sim в headless через docker-compose"
	@echo "  gui             - запустить Isaac Sim с GUI через docker-compose"
	@echo "  stop-headless   - остановить контейнер из headless файла"
	@echo "  stop-gui        - остановить GUI контейнер"
	@echo "  logs-headless   - показать логи headless"
	@echo "  logs-gui        - показать логи GUI"
	@echo "  check           - запустить compatibility_check внутри контейнера"
	@echo "  script-headless - запуск через scripts/start_isaac.sh headless"
	@echo "  script-gui      - запуск через scripts/start_isaac.sh gui"
	@echo "  clean           - удалить локальные кеши/логи (tmp/)"

env:
	@[ -f $(ENV_FILE) ] && echo "$(ENV_FILE) уже существует" || cp .env.example $(ENV_FILE)

prepare-root:
	mkdir -p $(ISAAC_ROOT)/cache/main $(ISAAC_ROOT)/cache/computecache $(ISAAC_ROOT)/logs $(ISAAC_ROOT)/config $(ISAAC_ROOT)/data $(ISAAC_ROOT)/pkg
	-chown -R $$(id -u):$$(id -g) $(ISAAC_ROOT) 2>/dev/null || true

headless: prepare-root
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_HEADLESS) up -d

gui: prepare-root
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_GUI) up -d

stop-headless:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_HEADLESS) down

stop-gui:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_GUI) down

logs-headless:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_HEADLESS) logs -f

logs-gui:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_GUI) logs -f

check: prepare-root
	IMAGE=$$(grep '^IMAGE=' $(ENV_FILE) | cut -d'=' -f2) ; \
	docker run --rm --gpus all --network host \
	  -u "$$(id -u):$$(id -g)" \
	  -v $(ISAAC_ROOT)/cache/main:/isaac-sim/.cache:rw \
	  -v $(ISAAC_ROOT)/cache/computecache:/isaac-sim/.nv/ComputeCache:rw \
	  -v $(ISAAC_ROOT)/logs:/isaac-sim/.nvidia-omniverse/logs:rw \
	  -v $(ISAAC_ROOT)/config:/isaac-sim/.nvidia-omniverse/config:rw \
	  -v $(ISAAC_ROOT)/data:/isaac-sim/.local/share/ov/data:rw \
	  -v $(ISAAC_ROOT)/pkg:/isaac-sim/.local/share/ov/pkg:rw \
	  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y $$IMAGE ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window

script-headless:
	./scripts/start_isaac.sh headless $(ISAAC_ROOT)

script-gui:
	DISPLAY=$${DISPLAY:-:0} ./scripts/start_isaac.sh gui $(ISAAC_ROOT)

clean:
	rm -rf $(ISAAC_ROOT)/cache $(ISAAC_ROOT)/logs $(ISAAC_ROOT)/config $(ISAAC_ROOT)/data $(ISAAC_ROOT)/pkg
