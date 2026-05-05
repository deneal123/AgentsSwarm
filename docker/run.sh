#!/bin/bash
set -e

# ============================================================================
# MLservice Run Script
# ============================================================================
#
# Использование:
#   ./run.sh [OPTIONS]
#
# Опции:
#   --dev          Запуск в режиме разработки (по умолчанию)
#   --prod         Запуск в продакшн режиме
#   --stop         Остановить все сервисы
#   --restart      Перезапустить все сервисы
#   --logs [NAME]  Показать логи (опционально: имя контейнера)
#   --status       Показать статус сервисов
#   -h, --help     Показать это сообщение
#
# Примеры:
#   ./run.sh                    # Запуск dev окружения
#   ./run.sh --prod             # Запуск prod окружения
#   ./run.sh --stop             # Остановка всех сервисов
#   ./run.sh --logs             # Просмотр логов всех сервисов
#   ./run.sh --logs backend     # Просмотр логов backend
#   ./run.sh --status           # Статус контейнеров
#
# Архитектура:
#   Основной стек (docker-compose*.yaml):
#     - frontend    : React приложение (порт 3000)
#     - backend     : FastAPI сервер (порт 8000)
#     - postgres    : База данных PostgreSQL
#     - redis       : Кэш и результаты Celery
#     - celery      : Воркер для фоновых задач
#     - minio       : S3-совместимое хранилище (порт 9000, UI: 9001)
#     - nginx       : Reverse proxy (порт 80)
#
# ============================================================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Переходим в директорию скрипта
cd "$(dirname "$0")" || exit 1

# Параметры по умолчанию
MODE="dev"
MODE_EXPLICIT=false
ACTION="start"
LOG_SERVICE=""
RELEASE=false
DOCKERHUB_REPO=""
TAG=""
STATE_DIR=".run-state"
NGINX_TEMPLATES_DIR="../infra/nginx/templates"

# Функция вывода справки
show_help() {
    head -50 "$0" | tail -45 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Функции логирования
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

compute_templates_fingerprint() {
    if [ ! -d "$NGINX_TEMPLATES_DIR" ]; then
        echo ""
        return 0
    fi

    find "$NGINX_TEMPLATES_DIR" -type f | sort | while IFS= read -r file_path; do
        sha256sum "$file_path"
    done | sha256sum | awk '{print $1}'
}

nginx_service_exists() {
    "${COMPOSE_CMD[@]}" config --services 2>/dev/null | grep -qx "nginx"
}

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            MODE_EXPLICIT=true
            shift
            ;;
        --prod)
            MODE="prod"
            MODE_EXPLICIT=true
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --logs)
            ACTION="logs"
            shift
            # Проверяем, есть ли следующий аргумент и не является ли он опцией
            if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
                LOG_SERVICE="$1"
                shift
            fi
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --release)
            RELEASE=true
            shift
            ;;
        --docker-repo)
            DOCKERHUB_REPO="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Неизвестная опция: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Авто-определение режима для read-only действий, если режим явно не указан.
# Это помогает командам --logs/--status корректно работать после запуска в --prod.
detect_active_mode() {
    local dev_running=false
    local prod_running=false

    if docker compose --env-file .env.dev -p gpthub-dev -f docker-compose.dev.yaml --profile dev --profile celery ps --status running -q 2>/dev/null | grep -q .; then
        dev_running=true
    fi

    if docker compose --env-file .env.prod -p gpthub-prod -f docker-compose.yaml --profile prod --profile celery ps --status running -q 2>/dev/null | grep -q .; then
        prod_running=true
    fi

    if [ "$prod_running" = true ] && [ "$dev_running" = false ]; then
        MODE="prod"
        log_info "Авто-режим: обнаружены запущенные prod-сервисы, использую --prod"
    elif [ "$dev_running" = true ] && [ "$prod_running" = false ]; then
        MODE="dev"
        log_info "Авто-режим: обнаружены запущенные dev-сервисы, использую --dev"
    fi
}

if [ "$MODE_EXPLICIT" = false ] && { [ "$ACTION" = "logs" ] || [ "$ACTION" = "status" ]; }; then
    detect_active_mode
fi

# Определение compose файла
if [ "$MODE" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yaml"
    PROJECT_NAME="gpthub-dev"
else
    COMPOSE_FILE="docker-compose.yaml"
    PROJECT_NAME="gpthub-prod"
fi
ENV_FILE=".env.${MODE}"
APP_DOMAIN=${APP_DOMAIN:-${APP__DOMAIN:-${SERVICE__APP_DOMAIN:-""}}}

if [ -z "$APP_DOMAIN" ] && [ -f "$ENV_FILE" ]; then
    APP_DOMAIN=$(awk -F= '
        /^[[:space:]]*(APP_DOMAIN|APP__DOMAIN|SERVICE__APP_DOMAIN)=/ {
            key=$1
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
            value=substr($0, index($0, "=")+1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
            gsub(/^"|"$/, "", value)
            gsub(/^\047|\047$/, "", value)
            domain=value
        }
        END { if (domain != "") print domain }
    ' "$ENV_FILE")
fi

APP_DOMAIN=${APP_DOMAIN:-"localhost"}

COMPOSE_CMD=(docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile "$MODE" --profile celery)

# Функция проверки здоровья сервиса
wait_for_service() {
    local service_name=$1
    local max_attempts=${2:-30}
    local attempt=1

    log_step "Ожидание $service_name..."

    while [ $attempt -le $max_attempts ]; do
    if "${COMPOSE_CMD[@]}" ps "$service_name" 2>/dev/null | grep -q "healthy\|running"; then
            log_success "$service_name готов"
            return 0
        fi
        sleep 2
        ((attempt++))
    done

    log_warning "$service_name не ответил за отведенное время"
    return 1
}

# Функция остановки сервисов
stop_services() {
    log_info "Остановка сервисов..."

    "${COMPOSE_CMD[@]}" down

    # Удаление временного .env файла
    if [ -f ".env" ]; then
        rm .env
        log_info "Удален временный .env файл"
    fi

    log_success "Все сервисы остановлены"
}

# Функция показа логов
show_logs() {
    if [ -n "$LOG_SERVICE" ]; then
        log_info "Логи сервиса $LOG_SERVICE (Ctrl+C для выхода)..."
    "${COMPOSE_CMD[@]}" logs -f "$LOG_SERVICE"
    else
        log_info "Логи всех сервисов (Ctrl+C для выхода)..."
    "${COMPOSE_CMD[@]}" logs -f
    fi
}

# Функция показа статуса
show_status() {
    log_info "Статус основных сервисов:"
    "${COMPOSE_CMD[@]}" ps
}

# Функция запуска сервисов
start_services() {
    log_info "============================================"
    log_info "Startup"
    log_info "============================================"
    log_info "Режим: $MODE"
    log_info "Compose файл: $COMPOSE_FILE"
    log_info "Compose project: $PROJECT_NAME"
    log_info "============================================"

    # Проверка наличия compose файла
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Файл $COMPOSE_FILE не найден!"
        log_info "Сначала выполните: ./build.sh --$MODE"
        exit 1
    fi

    # Проверяем env файл для интерполяции переменных
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Файл $ENV_FILE не найден!"
        exit 1
    fi

    # Запуск основного стека
    log_info ""
    log_step "Запуск основного стека..."

    mkdir -p "$STATE_DIR"

    local templates_fingerprint
    templates_fingerprint=$(compute_templates_fingerprint)
    local templates_state_file="${STATE_DIR}/nginx-templates-${MODE}.sha256"
    local force_recreate_nginx=false

    if [ -n "$templates_fingerprint" ] && nginx_service_exists; then
        if [ -f "$templates_state_file" ]; then
            local previous_fingerprint
            previous_fingerprint=$(cat "$templates_state_file")
            if [ "$previous_fingerprint" != "$templates_fingerprint" ]; then
                force_recreate_nginx=true
                log_warning "Обнаружены изменения в infra/nginx/templates/* — nginx будет пересоздан (--force-recreate nginx)"
            fi
        elif "${COMPOSE_CMD[@]}" ps -q nginx 2>/dev/null | grep -q .; then
            force_recreate_nginx=true
            log_warning "Не найден state шаблонов nginx для режима ${MODE}, но nginx уже существует — выполняю первичную синхронизацию (--force-recreate nginx)"
        fi
    fi

    if [ "$force_recreate_nginx" = true ]; then
        "${COMPOSE_CMD[@]}" up -d --force-recreate nginx
        "${COMPOSE_CMD[@]}" up -d
    else
        "${COMPOSE_CMD[@]}" up -d
    fi

    if [ -n "$templates_fingerprint" ]; then
        echo "$templates_fingerprint" > "$templates_state_file"
    fi

    # Ожидание ключевых сервисов
    log_info ""
    log_step "Ожидание готовности сервисов..."
    sleep 5

    # Вывод информации о доступе
    log_info ""
    log_info "============================================"
    log_success "Сервисы запущены!"
    log_info "============================================"
    log_info ""
    log_info "Доступные адреса:"

    if [ "$MODE" = "prod" ]; then
        log_info "  Frontend:    http://${APP_DOMAIN}"
        log_info "  Backend API: http://${APP_DOMAIN}/api"
        log_info "  MINIO UI:      http://${APP_DOMAIN}:9001"
    else
        log_info "  Frontend:    http://localhost:3000"
        log_info "  Backend API: http://localhost:8000"
        log_info "  API Docs:    http://localhost:8000/docs"
        log_info "  MINIO UI:    http://localhost:9001"
        
    fi

    log_info ""
    log_info "Команды:"
    log_info "  Логи:        ./docker/run.sh --logs"
    log_info "  Статус:      ./docker/run.sh --status"
    log_info "  Остановка:   ./docker/run.sh --stop"
    if [ "$RUN_TPOT" = true ]; then
        log_info "  Остановка всего: ./run.sh --stop --tpot"
    fi
}

# Выполнение выбранного действия
case $ACTION in
    start)
        start_services
        ;;
    start-release)
        if [ "$RELEASE" = true ]; then
            log_info "Performing release build before start: ${DOCKERHUB_REPO}:${TAG}"
            BUILD_OPTS=""
            if [ -n "$DOCKERHUB_REPO" ] && [ -n "$TAG" ]; then
                ./build.sh --prod --docker-repo "$DOCKERHUB_REPO" --tag "$TAG" $BUILD_OPTS
            else
                ./build.sh --prod $BUILD_OPTS
            fi
        fi
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        echo ""
        start_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
esac
