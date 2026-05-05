# Makefile for Eater

.PHONY: build test lint run
.PHONY: frontend-analyze

DOCKERHUB_REPO ?= mydockerhubuser 
TAG ?= latest
IMAGE := $(DOCKERHUB_REPO):$(TAG)
NO_CACHE ?= false
DOCKER_BUILD_ARGS ?=
BUILD_CONTEXT_BACKEND ?= .
MODE ?= dev

ifeq ($(NO_CACHE),true)
	NO_CACHE_FLAG = --no-cache
else
	NO_CACHE_FLAG =
endif

build:
	@echo "Building backend image $(IMAGE)..."
	@echo "Context: $(BUILD_CONTEXT_BACKEND)  Args: $(DOCKER_BUILD_ARGS)  NoCache: $(NO_CACHE)"
	@if [ -x docker/build.sh ]; then \
	  echo "Detected docker/build.sh — delegating build to script"; \
	  BUILD_OPTS=""; \
	  if [ "$(NO_CACHE)" = "true" ]; then BUILD_OPTS="$$BUILD_OPTS --no-cache"; fi; \
	  docker/build.sh --$(MODE) $$BUILD_OPTS; \
	else \
	  docker build $(NO_CACHE_FLAG) $(DOCKER_BUILD_ARGS) -t $(IMAGE) -f backend/Dockerfile $(BUILD_CONTEXT_BACKEND); \
	fi

test:
	@echo "Running all tests (backend + frontend)..."
	$(MAKE) test
	@echo "Running frontend integration tests..."
	if [ -d frontend ] && command -v npm >/dev/null 2>&1; then \
		cd frontend && npm run test:integration -- --passWithNoTests; \
	else \
		echo "Skipping frontend integration tests: npm not available in this environment"; \
	fi
	@echo "Running frontend e2e tests..."
	if [ -d frontend ] && command -v npm >/dev/null 2>&1; then \
		cd frontend && npm run e2e:run; \
	else \
		echo "Skipping frontend e2e tests: npm not available in this environment"; \
	fi

lint:
	@echo "Running pre-commit hooks and frontend lint..."
	pre-commit run --all-files || true
	# Frontend lint (optional if node is available)
	if [ -d frontend ] && command -v npm >/dev/null 2>&1; then \
	  echo "Running frontend linter..."; \
	  npm --prefix frontend run lint || true; \
	fi
	@echo "Formatting frontend sources with Prettier..."
	cd frontend && npm run format


run:
	@echo "Running services via docker/run.sh (defaults to --dev)"
	@if [ -x docker/run.sh ]; then \
	  docker/run.sh --$(MODE); \
	else \
	  echo "run.sh not found or not executable"; exit 1; \
	fi

stop:
	@echo "Stopping services via docker/run.sh --stop"
	@if [ -x docker/run.sh ]; then \
	  docker/run.sh --stop; \
	else \
	  echo "run.sh not found or not executable"; exit 1; \
	fi

frontend-analyze:
	@echo "Run frontend bundle analysis (source-map-explorer)..."
	cd frontend && npm run build:analyze
