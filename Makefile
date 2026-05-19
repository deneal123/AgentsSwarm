.PHONY: help init update pull status sync clean-all

# Цвета для вывода
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m # No Color

help: ## Показать доступные команды
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

init: ## Инициализировать и рекурсивно скачать все сабмодули
	@echo "$(GREEN)▶ Инициализация сабмодулей...$(NC)"
	git submodule update --init --recursive
	@echo "$(GREEN)✓ Готово$(NC)"

update: ## Обновить все сабмодули до последних коммитов (fetch + merge)
	@echo "$(GREEN)▶ Обновление всех сабмодулей...$(NC)"
	git submodule update --remote --recursive --merge
	@echo "$(GREEN)✓ Сабмодули обновлены$(NC)"

pull: ## Выполнить git pull для всех сабмодулей (обновить ссылки)
	@echo "$(GREEN)▶ Pull всех сабмодулей...$(NC)"
	git pull --recurse-submodules
	git submodule foreach --recursive git pull origin main || true
	git submodule foreach --recursive git pull origin master || true
	@echo "$(GREEN)✓ Готово$(NC)"

status: ## Показать статус всех сабмодулей
	@echo "$(GREEN)▶ Статус сабмодулей:$(NC)"
	@git submodule status --recursive
	@echo ""
	@echo "$(YELLOW)▶ Детальный статус каждого сабмодуля:$(NC)"
	@git submodule foreach --recursive 'echo "$(GREEN)📁 $$name$(NC)"; git status -s || true; echo ""'

sync: update pull ## Полное обновление: update + pull (рекомендуется)
	@echo "$(GREEN)✓ Все сабмодули синхронизированы$(NC)"

clean-all: ## Очистить и переинициализировать все сабмодули (осторожно!)
	@echo "$(RED)⚠ ВНИМАНИЕ! Это удалит локальные изменения во всех сабмодулях!$(NC)"
	@read -p "Вы уверены? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)▶ Очистка сабмодулей...$(NC)"; \
		git submodule deinit -f --all; \
		git submodule update --init --recursive; \
		echo "$(GREEN)✓ Сабмодули переинициализированы$(NC)"; \
	else \
		echo "$(RED)Отменено$(NC)"; \
	fi

commit-all: ## Закоммитить изменения во всех сабмодулях
	@echo "$(YELLOW)▶ Поиск изменений в сабмодулях...$(NC)"
	@git submodule foreach --recursive 'git add . && git commit -m "Auto-update from main repo" || true'
	@echo "$(GREEN)✓ Готово$(NC)"

# Альтернативная команда для старых версий Git
legacy-update:
	@echo "$(GREEN)▶ Ручное обновление сабмодулей (для старых версий Git)...$(NC)"
	git submodule foreach --recursive git fetch
	git submodule foreach --recursive git checkout main || true
	git submodule foreach --recursive git checkout master || true
	git submodule foreach --recursive git pull
	@echo "$(GREEN)✓ Готово$(NC)"