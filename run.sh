#!/usr/bin/env bash
# =============================================================================
# run.sh — запуск платформы AgentsSwarm
#
# Использование:
#   ./run.sh                   # dev-режим без GPU
#   ./run.sh --dev             # dev-режим без GPU (явно)
#   ./run.sh --prod            # production-режим
#   ./run.sh --gpu             # dev-режим + AI-сервисы с GPU
#   ./run.sh --dev --gpu       # то же самое
#   ./run.sh --prod --gpu      # production + GPU
#   ./run.sh --monitoring      # + Prometheus / Grafana / Jaeger
#   ./run.sh --down            # остановить все сервисы
# =============================================================================

set -euo pipefail

# ─── Цвета ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Аргументы ────────────────────────────────────────────────────────────────
MODE="dev"
GPU=false
MONITORING=false
ACTION="up"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)      MODE="dev"; shift ;;
        --prod)     MODE="prod"; shift ;;
        --gpu)      GPU=true; shift ;;
        --no-gpu)   GPU=false; shift ;;
        --monitoring) MONITORING=true; shift ;;
        --down)     ACTION="down"; shift ;;
        --help|-h)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            echo -e "${RED}❌  Неизвестный аргумент: $1${NC}"
            exit 1
            ;;
    esac
done

# ─── Баннер ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          AgentsSwarm Platform            ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  Режим      : ${BOLD}${MODE}${NC}"
echo -e "  GPU        : ${BOLD}${GPU}${NC}"
echo -e "  Monitoring : ${BOLD}${MONITORING}${NC}"
echo ""

# ─── Проверка зависимостей ────────────────────────────────────────────────────
check_deps() {
    echo -e "${CYAN}▶  Проверка зависимостей...${NC}"

    # Docker
    if ! command -v docker &>/dev/null; then
        echo -e "${RED}❌  Docker не найден. Установите: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC}  Docker $(docker --version | awk '{print $3}' | tr -d ',')"

    # Docker Compose
    if ! docker compose version &>/dev/null 2>&1; then
        echo -e "${RED}❌  Docker Compose v2 не найден. Обновите Docker Desktop или установите плагин.${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC}  Docker Compose $(docker compose version --short)"

    # .env
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            echo -e "${YELLOW}⚠️   .env не найден, копирую из .env.example...${NC}"
            cp .env.example .env
            echo -e "  ${YELLOW}⚠️   Отредактируйте .env перед запуском production!${NC}"
        else
            echo -e "${RED}❌  .env не найден и .env.example тоже отсутствует.${NC}"
            exit 1
        fi
    fi
    echo -e "  ${GREEN}✓${NC}  .env найден"

    # GPU (если запрошен)
    if [[ "$GPU" == true ]]; then
        if ! command -v nvidia-smi &>/dev/null; then
            echo -e "${YELLOW}⚠️   nvidia-smi не найден. GPU-сервисы могут не запуститься.${NC}"
        else
            echo -e "  ${GREEN}✓${NC}  NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
        fi

        if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &>/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️   nvidia-container-toolkit может быть не установлен. GPU-сервисы могут упасть.${NC}"
        else
            echo -e "  ${GREEN}✓${NC}  nvidia-container-toolkit работает"
        fi
    fi

    echo ""
}

# ─── Остановка ────────────────────────────────────────────────────────────────
do_down() {
    echo -e "${CYAN}▶  Остановка сервисов...${NC}"
    if [[ "$MODE" == "prod" ]]; then
        docker compose -f docker-compose.yml down
    else
        docker compose -f docker-compose.dev.yml down
    fi
    echo -e "${GREEN}✅  Все сервисы остановлены.${NC}"
}

# ─── Запуск ───────────────────────────────────────────────────────────────────
do_up() {
    check_deps

    local compose_files="-f docker-compose.dev.yml"
    local profiles=""

    if [[ "$MODE" == "prod" ]]; then
        compose_files="-f docker-compose.yml"
    fi

    if [[ "$GPU" == true ]]; then
        profiles="$profiles --profile gpu"
    fi

    if [[ "$MONITORING" == true ]]; then
        profiles="$profiles --profile monitoring"
    fi

    echo -e "${CYAN}▶  Запуск инфраструктуры (БД, брокеры)...${NC}"
    docker compose $compose_files up -d postgres influxdb neo4j redis minio emqx rabbitmq

    echo -e "${CYAN}▶  Ожидание готовности сервисов (healthcheck)...${NC}"
    local max_wait=120
    local elapsed=0
    while [[ $elapsed -lt $max_wait ]]; do
        local unhealthy
        unhealthy=$(docker compose $compose_files ps --format json 2>/dev/null \
            | python3 -c "
import sys, json
data = sys.stdin.read().strip()
if not data: exit(0)
lines = [l for l in data.split('\n') if l.strip()]
count = sum(1 for l in lines if json.loads(l).get('Health','') in ('starting','unhealthy'))
print(count)
" 2>/dev/null || echo "0")

        if [[ "$unhealthy" -eq 0 ]]; then
            break
        fi
        echo -e "  ⏳  Ожидание... ($elapsed/${max_wait}s, unhealthy: $unhealthy)"
        sleep 5
        elapsed=$(( elapsed + 5 ))
    done

    echo -e "${CYAN}▶  Запуск application-сервисов...${NC}"
    docker compose $compose_files $profiles up -d

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅  AgentsSwarm запущен в режиме: ${BOLD}${MODE}${NC}${GREEN}             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Доступные интерфейсы:${NC}"
    echo -e "  Frontend          →  http://localhost:3000"
    echo -e "  API Gateway       →  http://localhost:8005/docs"
    echo -e "  RabbitMQ UI       →  http://localhost:15672  (guest/guest)"
    echo -e "  EMQX Dashboard    →  http://localhost:18083"
    echo -e "  MinIO Console     →  http://localhost:9001"
    echo -e "  Neo4j Browser     →  http://localhost:7474"
    echo -e "  InfluxDB UI       →  http://localhost:8086"
    echo -e "  Redis Insight     →  http://localhost:8001"
    if [[ "$MONITORING" == true ]]; then
        echo -e "  Grafana           →  http://localhost:3001"
        echo -e "  Jaeger UI         →  http://localhost:16686"
        echo -e "  Prometheus        →  http://localhost:9090"
    fi
    echo ""
    echo -e "  Логи: ${CYAN}make logs${NC}   Статус: ${CYAN}make ps${NC}   Стоп: ${CYAN}./run.sh --down${NC}"
    echo ""
}

# ─── Точка входа ──────────────────────────────────────────────────────────────
if [[ "$ACTION" == "down" ]]; then
    do_down
else
    do_up
fi
