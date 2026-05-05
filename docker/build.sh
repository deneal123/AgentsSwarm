#!/bin/bash
set -e

# ============================================================================
# MLservice Build Script
# ============================================================================
#
# Использование:
#   ./build.sh [OPTIONS]
#
# Опции:
#   --dev          Сборка для режима разработки (по умолчанию)
#   --prod         Сборка для продакшн режима
#   --no-cache     Сборка без использования кэша Docker
#   -h, --help     Показать это сообщение
#
# Примеры:
#   ./build.sh                 # Сборка dev окружения
#   ./build.sh --prod          # Сборка prod окружения
#   ./build.sh --no-cache      # Пересборка без кэша
#
# ============================================================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переходим в директорию скрипта
cd "$(dirname "$0")" || exit 1

# Параметры по умолчанию
MODE="dev"
NO_CACHE=""
DOCKERHUB_REPO=""
TAG=""

# Функция вывода справки
show_help() {
    head -30 "$0" | tail -25 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Функция логирования
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

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            shift
            ;;
        --prod)
            MODE="prod"
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
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

# Определение compose файла
if [ "$MODE" = "dev" ]; then
    COMPOSE_FILE="docker-compose.dev.yaml"
    PROJECT_NAME="agents-swarm-dev"
else
    COMPOSE_FILE="docker-compose.yaml"
    PROJECT_NAME="agents-swarm-prod"
fi
ENV_FILE=".env.${MODE}"

log_info "============================================"
log_info "Build"
log_info "============================================"
log_info "Режим: $MODE"
log_info "Compose файл: $COMPOSE_FILE"
log_info "Compose project: $PROJECT_NAME"
if [ -n "$DOCKERHUB_REPO" ] && [ -n "$TAG" ]; then
    log_info "Release tagging: ${DOCKERHUB_REPO}:${TAG}"
fi
if [ -n "$NO_CACHE" ]; then
    log_info "Кэш: отключен"
fi
log_info "============================================"

# Проверка наличия compose файла
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Файл $COMPOSE_FILE не найден!"
    exit 1
fi

# Проверка наличия env файла для интерполяции docker compose
if [ ! -f "$ENV_FILE" ]; then
    log_error "Файл $ENV_FILE не найден!"
    log_error "Docker Compose не сможет корректно подставить переменные окружения."
    exit 1
fi

# Сборка основного стека
log_info "Сборка основного стека..."
docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile "$MODE" build $NO_CACHE

if [ $? -eq 0 ]; then
    log_success "Основной стек собран успешно"
else
    log_error "Ошибка сборки основного стека"
    exit 1
fi

# If release repo/tag provided - tag built images for push
if [ -n "$DOCKERHUB_REPO" ] && [ -n "$TAG" ]; then
    log_info "Tagging images for release: ${DOCKERHUB_REPO}:${TAG}"
    # Tag backend image explicitly using backend Dockerfile/build context
    if [ -d backend ]; then
        log_info "Tagging backend image as ${DOCKERHUB_REPO}:${TAG}"
        docker build $NO_CACHE -t "${DOCKERHUB_REPO}:${TAG}" -f backend/Dockerfile backend || \
            log_warning "Failed to tag backend image via direct build"
    fi
    # Optionally tag frontend image (suffix -frontend)
    if [ -d frontend ]; then
        FRONT_TAG="${DOCKERHUB_REPO}-frontend:${TAG}"
        log_info "Tagging frontend image as ${FRONT_TAG}"
        docker build $NO_CACHE -t "${FRONT_TAG}" -f frontend/Dockerfile frontend || \
            log_warning "Failed to tag frontend image via direct build"
    fi
fi

log_info ""
log_info "============================================"
log_success "Сборка завершена!"
log_info "============================================"
log_info ""
