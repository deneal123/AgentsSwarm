#!/usr/bin/env bash
# =============================================================================
# build.sh — сборка Docker-образов AgentsSwarm
#
# Использование:
#   ./build.sh                       # собрать все образы
#   ./build.sh --service gateway     # собрать один сервис
#   ./build.sh --push                # собрать и запушить в registry
#   ./build.sh --service vllm --push
# =============================================================================

set -euo pipefail

# ─── Конфигурация ─────────────────────────────────────────────────────────────
REGISTRY="${REGISTRY:-ghcr.io/deneal123/agentsswarm}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Сервисы и их Dockerfile (относительно корня репозитория)
declare -A SERVICES=(
    [gateway]="services/gateway_service"
    [orchestrator]="services/orchestrator"
    [vllm]="services/vllm_service"
    [smolvla]="services/smolvla_service"
    [communication]="services/communication_service"
    [robot-edge]="services/robot_edge"
    [frontend]="services/frontend"
)

# ─── Аргументы ────────────────────────────────────────────────────────────────
SELECTED_SERVICE=""
PUSH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --service|-s)
            SELECTED_SERVICE="$2"
            shift 2
            ;;
        --push|-p)
            PUSH=true
            shift
            ;;
        --help|-h)
            sed -n '2,10p' "$0"
            exit 0
            ;;
        *)
            echo "❌  Неизвестный аргумент: $1"
            exit 1
            ;;
    esac
done

# ─── Функции ──────────────────────────────────────────────────────────────────
build_image() {
    local name="$1"
    local context="$2"

    if [[ ! -d "$context" ]]; then
        echo "⚠️   Пропуск $name: директория $context не найдена"
        return 0
    fi

    local image="${REGISTRY}/${name}"
    local tags="-t ${image}:${GIT_SHA} -t ${image}:latest"

    if [[ -n "$GIT_TAG" ]]; then
        tags="$tags -t ${image}:${GIT_TAG}"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  🔨  Сборка: ${name}"
    echo "  📁  Контекст: ${context}"
    echo "  🏷️   Теги: sha=${GIT_SHA}${GIT_TAG:+, version=$GIT_TAG}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    docker build \
        ${tags} \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg GIT_SHA="${GIT_SHA}" \
        --build-arg GIT_TAG="${GIT_TAG:-dev}" \
        --label "org.opencontainers.image.created=${BUILD_DATE}" \
        --label "org.opencontainers.image.revision=${GIT_SHA}" \
        --label "org.opencontainers.image.version=${GIT_TAG:-dev}" \
        "${context}"

    if [[ "$PUSH" == true ]]; then
        echo "  📤  Push: ${image}..."
        docker push "${image}:${GIT_SHA}"
        docker push "${image}:latest"
        if [[ -n "$GIT_TAG" ]]; then
            docker push "${image}:${GIT_TAG}"
        fi
    fi
}

# ─── Главный блок ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         AgentsSwarm — Docker Build               ║"
echo "╚══════════════════════════════════════════════════╝"
echo "  Registry : ${REGISTRY}"
echo "  Git SHA  : ${GIT_SHA}"
echo "  Git Tag  : ${GIT_TAG:-none}"
echo "  Push     : ${PUSH}"
echo ""

START_TIME=$(date +%s)

if [[ -n "$SELECTED_SERVICE" ]]; then
    # Сборка одного сервиса
    if [[ -z "${SERVICES[$SELECTED_SERVICE]+_}" ]]; then
        echo "❌  Неизвестный сервис: ${SELECTED_SERVICE}"
        echo "    Доступные: ${!SERVICES[*]}"
        exit 1
    fi
    build_image "$SELECTED_SERVICE" "${SERVICES[$SELECTED_SERVICE]}"
else
    # Сборка всех сервисов
    FAILED=()
    for name in "${!SERVICES[@]}"; do
        if ! build_image "$name" "${SERVICES[$name]}"; then
            FAILED+=("$name")
        fi
    done

    if [[ ${#FAILED[@]} -gt 0 ]]; then
        echo ""
        echo "❌  Ошибка сборки: ${FAILED[*]}"
        exit 1
    fi
fi

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

echo ""
echo "✅  Сборка завершена за ${ELAPSED}s"
