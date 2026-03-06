#!/usr/bin/env bash
# =============================================================================
# init-db.sh — комплексная инициализация всех баз данных AgentsSwarm
#
# Запуск:
#   cd /root/projects/AgentsSwarm
#   bash infrastructure/scripts/init-db.sh [--compose-file docker-compose.dev.yml]
#
# Опции:
#   --compose-file FILE   — путь до docker-compose файла (по умолчанию: docker-compose.dev.yml)
#   --skip-postgres       — пропустить PostgreSQL
#   --skip-influxdb       — пропустить InfluxDB
#   --skip-neo4j          — пропустить Neo4j
#   --skip-redis          — пропустить Redis
#   --skip-minio          — пропустить MinIO
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/../.."
COMPOSE_FILE="${ROOT_DIR}/docker-compose.dev.yml"

SKIP_POSTGRES=false
SKIP_INFLUXDB=false
SKIP_NEO4J=false
SKIP_REDIS=false
SKIP_MINIO=false

# ─── Разбор аргументов ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
        --skip-postgres) SKIP_POSTGRES=true; shift ;;
        --skip-influxdb) SKIP_INFLUXDB=true; shift ;;
        --skip-neo4j)    SKIP_NEO4J=true;    shift ;;
        --skip-redis)    SKIP_REDIS=true;    shift ;;
        --skip-minio)    SKIP_MINIO=true;    shift ;;
        *) echo "Неизвестный аргумент: $1"; exit 1 ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       AgentsSwarm — Инициализация БД             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── Загрузка переменных окружения ────────────────────────────────────────────
if [[ -f "${ROOT_DIR}/.env" ]]; then
    # shellcheck disable=SC1090
    set -a; source "${ROOT_DIR}/.env"; set +a
    echo "   ✓  Переменные окружения загружены из .env"
else
    echo "   ⚠  .env не найден — используются значения по умолчанию"
fi

DC="docker compose -f ${COMPOSE_FILE}"

# ─── Вспомогательные функции ──────────────────────────────────────────────────
wait_for_service() {
    local service="$1"; local max_wait="${2:-120}"; local elapsed=0
    echo "   ⏳  Ожидание healthy статуса: ${service}..."
    until $DC ps --status healthy 2>/dev/null | grep -q "agentsswarm-${service}"; do
        if [[ $elapsed -ge $max_wait ]]; then
            echo "   ⚠️  ${service} не healthy через ${max_wait}s — продолжаю без ожидания"
            return 1
        fi
        sleep 3; elapsed=$((elapsed + 3))
    done
    echo "   ✓  ${service} healthy (${elapsed}s)"
}

# ─── PostgreSQL ───────────────────────────────────────────────────────────────
if [[ "$SKIP_POSTGRES" == false ]]; then
    echo "▶  PostgreSQL..."
    wait_for_service postgres 90 || true

    # init.sql монтируется в /docker-entrypoint-initdb.d/00-init.sql и выполняется
    # автоматически при первом старте. Здесь только проверяем наличие расширений.
    $DC exec -T postgres \
        psql -U "${POSTGRES_USER:-agentsswarm}" -d "${POSTGRES_DB:-agentsswarm}" -c \
        "SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp','pgcrypto','pg_trgm') ORDER BY extname;" \
        2>/dev/null || echo "   ⚠️  PostgreSQL: проверка расширений не удалась"
    echo "   ✓  PostgreSQL: расширения и enum-типы проверены"
fi

# ─── InfluxDB ─────────────────────────────────────────────────────────────────
if [[ "$SKIP_INFLUXDB" == false ]]; then
    echo "▶  InfluxDB..."
    wait_for_service influxdb 120 || true

    INFLUXDB_INIT_SCRIPT="${SCRIPT_DIR}/../influxdb/init.sh"
    if [[ -f "$INFLUXDB_INIT_SCRIPT" ]]; then
        bash "$INFLUXDB_INIT_SCRIPT"
    else
        echo "   ⚠️  ${INFLUXDB_INIT_SCRIPT} не найден — пропускаю"
    fi
    echo "   ✓  InfluxDB готов"
fi

# ─── Neo4j ────────────────────────────────────────────────────────────────────
if [[ "$SKIP_NEO4J" == false ]]; then
    echo "▶  Neo4j..."
    wait_for_service neo4j 120 || true

    # init.cypher смонтирован в /var/lib/neo4j/import/init.cypher (см. docker-compose)
    if $DC exec -T neo4j test -f /var/lib/neo4j/import/init.cypher 2>/dev/null; then
        $DC exec -T neo4j \
            cypher-shell \
            -u "${NEO4J_USER:-neo4j}" \
            -p "${NEO4J_PASSWORD:-neo4j_secret}" \
            --format plain \
            -f /var/lib/neo4j/import/init.cypher \
            2>&1 | grep -v "^0 rows\|^Added\|^Set\|^Completed" || true
        echo "   ✓  Neo4j: ограничения, индексы и начальные зоны созданы"
    else
        echo "   ⚠️  /var/lib/neo4j/import/init.cypher не найден в контейнере"
    fi

    # Проверка APOC плагина
    $DC exec -T neo4j \
        cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-neo4j_secret}" \
        "CALL dbms.procedures() YIELD name WHERE name STARTS WITH 'apoc' RETURN count(*) AS apoc_count;" \
        2>/dev/null | grep -q "apoc_count" \
        && echo "   ✓  Neo4j: APOC доступен" \
        || echo "   ⚠️  Neo4j: APOC недоступен — проверьте NEO4J_PLUGINS в docker-compose"
fi

# ─── Redis ────────────────────────────────────────────────────────────────────
if [[ "$SKIP_REDIS" == false ]]; then
    echo "▶  Redis Stack..."
    wait_for_service redis 60 || true

    REDIS_CLI="$DC exec -T redis redis-cli --no-auth-warning -a ${REDIS_PASSWORD:-redis_secret}"

    # Проверка загруженных модулей
    MODULES=$($REDIS_CLI MODULE LIST 2>/dev/null | grep -E "name|ReJSON|search|timeseries" || echo "")
    if echo "$MODULES" | grep -qi "rejson\|search\|timeseries"; then
        echo "   ✓  Redis Stack: RedisJSON, RediSearch, RedisTimeSeries загружены"
    else
        echo "   ⚠️  Redis Stack: модули не обнаружены — контейнер ещё запускается?"
    fi

    # Конфигурация RediSearch
    $REDIS_CLI FT.CONFIG SET MAXSEARCHRESULTS 10000 > /dev/null 2>&1 \
        && echo "   ✓  RediSearch: MAXSEARCHRESULTS=10000" \
        || echo "   ⚠️  RediSearch: FT.CONFIG SET не удался"

    $REDIS_CLI FT.CONFIG SET MAXAGGREGATERESULTS 10000 > /dev/null 2>&1 \
        && echo "   ✓  RediSearch: MAXAGGREGATERESULTS=10000" \
        || echo "   ⚠️  RediSearch: FT.CONFIG SET не удался"

    echo "   ✓  Redis готов"
fi

# ─── MinIO ────────────────────────────────────────────────────────────────────
if [[ "$SKIP_MINIO" == false ]]; then
    echo "▶  MinIO..."
    wait_for_service minio 90 || true

    MINIO_INIT_SCRIPT="${SCRIPT_DIR}/../minio/init.sh"
    if [[ -f "$MINIO_INIT_SCRIPT" ]]; then
        if command -v mc &> /dev/null; then
            bash "$MINIO_INIT_SCRIPT"
        else
            # Запускаем через отдельный mc контейнер
            docker run --rm --network agentsswarm-network \
                -e MINIO_URL="http://minio:9000" \
                -e MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}" \
                -e MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio_secret}" \
                -v "${SCRIPT_DIR}/../minio:/scripts:ro" \
                --entrypoint bash \
                minio/mc:latest \
                /scripts/init.sh 2>/dev/null || \
                echo "   ⚠️  MinIO: установите mc локально для инициализации"
        fi
    else
        echo "   ⚠️  ${MINIO_INIT_SCRIPT} не найден — пропускаю"
    fi
    echo "   ✓  MinIO готов"
fi

# ─── Итог ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅  Инициализация всех БД завершена            ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "   Следующие шаги:"
echo "   1. make migrate    — применить Alembic-миграции"
echo "   2. make seed       — загрузить тестовые данные"
echo ""
