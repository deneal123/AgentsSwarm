#!/usr/bin/env bash
# =============================================================================
# proto/scripts/gen-proto.sh
# Локальная генерация Protobuf/gRPC стабов через grpcio-tools
#
# Используется как fallback, когда buf registry недоступен или не настроен.
#
# Зависимости Python (устанавливаются автоматически если отсутствуют):
#   pip install grpcio-tools mypy-protobuf
#
# Зависимости Node.js (для TypeScript frontend):
#   npm install -g @bufbuild/protoc-gen-es @connectrpc/protoc-gen-connect-es
#
# Использование:
#   cd /root/projects/AgentsSwarm
#   bash proto/scripts/gen-proto.sh [--python-only] [--ts-only] [--no-pyi]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_DIR="${SCRIPT_DIR}/.."
ROOT_DIR="${PROTO_DIR}/.."

PYTHON_ONLY=false
TS_ONLY=false
NO_PYI=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python-only) PYTHON_ONLY=true; shift ;;
        --ts-only)     TS_ONLY=true;     shift ;;
        --no-pyi)      NO_PYI=true;      shift ;;
        *) echo "Неизвестный аргумент: $1"; exit 1 ;;
    esac
done

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_ok()   { echo -e "   ${GREEN}✓${NC}  $*"; }
log_warn() { echo -e "   ${YELLOW}⚠${NC}  $*"; }
log_err()  { echo -e "   ${RED}✗${NC}  $*"; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       AgentsSwarm — Proto Generation             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── Проверка зависимостей ────────────────────────────────────────────────────
if [[ "$TS_ONLY" == false ]]; then
    echo "▶  Проверка Python зависимостей..."
    if ! python3 -c "import grpc_tools" 2>/dev/null; then
        log_warn "grpcio-tools не установлен. Устанавливаю..."
        pip install --quiet grpcio-tools
    fi
    log_ok "grpcio-tools доступен"

    if [[ "$NO_PYI" == false ]]; then
        if ! python3 -c "import mypy_protobuf" 2>/dev/null; then
            log_warn "mypy-protobuf не установлен. Устанавливаю..."
            pip install --quiet mypy-protobuf
        fi
        log_ok "mypy-protobuf доступен"
    fi
fi

# ─── Определяем proto-файлы ───────────────────────────────────────────────────
PROTO_FILES=(
    "common/v1/types.proto"
    "common/v1/telemetry.proto"
    "gateway/v1/gateway.proto"
    "orchestrator/v1/orchestrator.proto"
    "inference/v1/triton.proto"
    "inference/v1/vllm.proto"
    "inference/v1/smolvla.proto"
)

# Путь к google/protobuf well-known types (через grpcio-tools)
PROTO_INCLUDE="$(python3 -c 'import grpc_tools, os; print(os.path.join(os.path.dirname(grpc_tools.__file__), "_proto"))' 2>/dev/null)"

# ─── Маппинг сервис → выходная директория ─────────────────────────────────────
declare -A SERVICE_DIRS=(
    ["gateway"]="${ROOT_DIR}/services/gateway_service/src/gateway/proto"
    ["orchestrator"]="${ROOT_DIR}/services/orchestrator/src/orchestrator/proto"
    ["vllm"]="${ROOT_DIR}/services/vllm_service/src/vllm_service/proto"
    ["triton"]="${ROOT_DIR}/services/triton_inference/src/triton_service/proto"
    ["smolvla"]="${ROOT_DIR}/services/smolvla_service/src/smolvla_service/proto"
    ["robot_edge"]="${ROOT_DIR}/services/robot_edge/src/robot_edge/proto"
)

# ─── Генерация Python стабов ──────────────────────────────────────────────────
if [[ "$TS_ONLY" == false ]]; then
    echo "▶  Генерация Python gRPC стабов..."

    for SERVICE in "${!SERVICE_DIRS[@]}"; do
        OUT_DIR="${SERVICE_DIRS[$SERVICE]}"
        mkdir -p "$OUT_DIR"

        # Генерируем все proto-файлы в каждую директорию сервиса
        PYI_FLAG=""
        if [[ "$NO_PYI" == false ]]; then
            PYI_FLAG="--mypy_out=${OUT_DIR} --mypy_grpc_out=${OUT_DIR}"
        fi

        # shellcheck disable=SC2086
        python3 -m grpc_tools.protoc \
            -I "${PROTO_DIR}" \
            -I "${PROTO_INCLUDE}" \
            --python_out="${OUT_DIR}" \
            --grpc_python_out="${OUT_DIR}" \
            ${PYI_FLAG} \
            "${PROTO_FILES[@]/#/${PROTO_DIR}/}" \
            2>/dev/null || {
                log_warn "${SERVICE}: некоторые proto-файлы пропущены (возможно, google/*.proto недоступны)"
            }

        # Создаём __init__.py для всех пакетов
        find "$OUT_DIR" -type d | while read -r DIR; do
            touch "${DIR}/__init__.py"
        done

        log_ok "Python: ${SERVICE} → ${OUT_DIR#${ROOT_DIR}/}"
    done
fi

# ─── Генерация TypeScript стабов (ConnectRPC) ─────────────────────────────────
if [[ "$PYTHON_ONLY" == false ]]; then
    echo "▶  Генерация TypeScript стабов (ConnectRPC)..."

    TS_OUT="${ROOT_DIR}/services/frontend/src/proto"
    mkdir -p "$TS_OUT"

    # Проверяем protoc-gen-es и protoc-gen-connect-es
    if command -v protoc-gen-es &>/dev/null && command -v protoc-gen-connect-es &>/dev/null; then
        python3 -m grpc_tools.protoc \
            -I "${PROTO_DIR}" \
            -I "${PROTO_INCLUDE}" \
            --plugin="protoc-gen-es=$(command -v protoc-gen-es)" \
            --es_out="${TS_OUT}" \
            --es_opt="target=ts" \
            --plugin="protoc-gen-connect-es=$(command -v protoc-gen-connect-es)" \
            --connect-es_out="${TS_OUT}" \
            --connect-es_opt="target=ts" \
            "${PROTO_FILES[@]/#/${PROTO_DIR}/}" \
            2>/dev/null
        log_ok "TypeScript (ConnectRPC): frontend/src/proto/"
    else
        log_warn "protoc-gen-es / protoc-gen-connect-es не найдены"
        log_warn "Установка: npm install -g @bufbuild/protoc-gen-es @connectrpc/protoc-gen-connect-es"
        log_warn "Или используйте buf generate (требует buf registry)"
    fi
fi

echo ""
echo "✅  Генерация завершена."
echo ""
echo "   Альтернатива через buf (требует buf registry):"
echo "   $ cd proto && buf generate"
echo ""
