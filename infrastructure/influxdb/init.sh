#!/usr/bin/env bash
# =============================================================================
# infrastructure/influxdb/init.sh
# Инициализация InfluxDB 2.x: бакеты, токены для каждого сервиса.
#
# Переменные окружения (можно задать в .env или передать явно):
#   INFLUXDB_URL              — URL InfluxDB (по умолчанию: http://localhost:8086)
#   INFLUXDB_ADMIN_TOKEN      — токен суперпользователя (создаётся при первом старте)
#   INFLUXDB_ORG              — имя организации (по умолчанию: agentsswarm)
#   INFLUXDB_BUCKET_TELEMETRY — имя основного бакета (по умолчанию: telemetry)
# =============================================================================

set -euo pipefail

INFLUX_URL="${INFLUXDB_URL:-http://localhost:8086}"
ADMIN_TOKEN="${INFLUXDB_ADMIN_TOKEN:-changeme-influx-admin-token}"
ORG="${INFLUXDB_ORG:-agentsswarm}"
BUCKET_TELEMETRY="${INFLUXDB_BUCKET_TELEMETRY:-telemetry}"

# Цвета для вывода
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log_ok()   { echo -e "   ${GREEN}✓${NC}  $*"; }
log_warn() { echo -e "   ${YELLOW}⚠${NC}  $*"; }
log_err()  { echo -e "   ${RED}✗${NC}  $*"; }

# ─── Ожидание готовности InfluxDB ─────────────────────────────────────────────
echo "▶  Ожидание готовности InfluxDB (${INFLUX_URL})..."
MAX_WAIT=60
ELAPSED=0
until curl -sf "${INFLUX_URL}/ping" > /dev/null 2>&1; do
    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        log_err "InfluxDB не отвечает через ${MAX_WAIT}s — прерываю"
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
log_ok "InfluxDB доступен (${ELAPSED}s)"

# ─── Вспомогательные функции ──────────────────────────────────────────────────
influx_api() {
    local method="$1"; local endpoint="$2"; local data="${3:-}"
    if [[ -n "$data" ]]; then
        curl -sf -X "$method" "${INFLUX_URL}${endpoint}" \
            -H "Authorization: Token ${ADMIN_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -sf -X "$method" "${INFLUX_URL}${endpoint}" \
            -H "Authorization: Token ${ADMIN_TOKEN}"
    fi
}

get_org_id() {
    influx_api GET "/api/v2/orgs?org=${ORG}" | \
        python3 -c "import sys,json; orgs=json.load(sys.stdin)['orgs']; print(orgs[0]['id']) if orgs else sys.exit(1)"
}

bucket_exists() {
    local name="$1"; local org_id="$2"
    influx_api GET "/api/v2/buckets?name=${name}&orgID=${org_id}" | \
        python3 -c "import sys,json; bs=json.load(sys.stdin)['buckets']; sys.exit(0) if bs else sys.exit(1)" 2>/dev/null
}

create_bucket() {
    local name="$1"; local org_id="$2"; local retention_seconds="$3"
    influx_api POST "/api/v2/buckets" \
        "{\"name\":\"${name}\",\"orgID\":\"${org_id}\",\"retentionRules\":[{\"type\":\"expire\",\"everySeconds\":${retention_seconds}}]}" \
        > /dev/null
}

# ─── Получение ID организации ─────────────────────────────────────────────────
echo "▶  Проверка организации '${ORG}'..."
ORG_ID="$(get_org_id)"
log_ok "Организация: ${ORG} (id=${ORG_ID})"

# ─── Бакеты ───────────────────────────────────────────────────────────────────
echo "▶  Создание бакетов..."

# telemetry — телеметрия роботов (90 дней = 7 776 000 s)
if bucket_exists "${BUCKET_TELEMETRY}" "${ORG_ID}"; then
    log_ok "Бакет '${BUCKET_TELEMETRY}' уже существует"
else
    create_bucket "${BUCKET_TELEMETRY}" "${ORG_ID}" 7776000
    log_ok "Бакет '${BUCKET_TELEMETRY}' создан (retention=90d)"
fi

# metrics — системные метрики сервисов (30 дней = 2 592 000 s)
if bucket_exists "metrics" "${ORG_ID}"; then
    log_ok "Бакет 'metrics' уже существует"
else
    create_bucket "metrics" "${ORG_ID}" 2592000
    log_ok "Бакет 'metrics' создан (retention=30d)"
fi

# events — события системы (7 дней = 604 800 s)
if bucket_exists "events" "${ORG_ID}"; then
    log_ok "Бакет 'events' уже существует"
else
    create_bucket "events" "${ORG_ID}" 604800
    log_ok "Бакет 'events' создан (retention=7d)"
fi

# audit-logs — аудит действий пользователей (365 дней = 31 536 000 s)
if bucket_exists "audit-logs" "${ORG_ID}"; then
    log_ok "Бакет 'audit-logs' уже существует"
else
    create_bucket "audit-logs" "${ORG_ID}" 31536000
    log_ok "Бакет 'audit-logs' создан (retention=365d)"
fi

# ─── Служебные API-токены ─────────────────────────────────────────────────────
# Примечание: токены создаются один раз. При повторном запуске можно пропустить,
# если соответствующие переменные окружения уже заданы.
echo "▶  Создание API-токенов для сервисов..."

# Вспомогательная функция: создать токен и вернуть строку токена
create_token() {
    local description="$1"; shift
    local permissions_json="$*"
    local result
    result=$(influx_api POST "/api/v2/authorizations" \
        "{\"orgID\":\"${ORG_ID}\",\"description\":\"${description}\",\"permissions\":[${permissions_json}]}")
    echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
}

# Получаем bucket IDs для построения разрешений
get_bucket_id() {
    local bname="$1"
    influx_api GET "/api/v2/buckets?name=${bname}&orgID=${ORG_ID}" | \
        python3 -c "import sys,json; bs=json.load(sys.stdin)['buckets']; print(bs[0]['id']) if bs else sys.exit(1)"
}

TELEMETRY_ID="$(get_bucket_id "${BUCKET_TELEMETRY}")"
METRICS_ID="$(get_bucket_id "metrics")"
EVENTS_ID="$(get_bucket_id "events")"

# ── orchestrator-write-token: запись в telemetry + events ──────────────────
if [[ -z "${INFLUXDB_ORCHESTRATOR_WRITE_TOKEN:-}" ]]; then
    ORCH_WRITE_TOKEN="$(create_token "orchestrator-write" \
        "{\"action\":\"write\",\"resource\":{\"type\":\"buckets\",\"id\":\"${TELEMETRY_ID}\",\"orgID\":\"${ORG_ID}\"}}" \
        ",{\"action\":\"write\",\"resource\":{\"type\":\"buckets\",\"id\":\"${EVENTS_ID}\",\"orgID\":\"${ORG_ID}\"}}" \
    )" || { log_warn "Не удалось создать orchestrator-write-token (возможно, уже существует)"; ORCH_WRITE_TOKEN=""; }
    [[ -n "$ORCH_WRITE_TOKEN" ]] && log_ok "orchestrator-write-token создан: ${ORCH_WRITE_TOKEN:0:16}..."
else
    log_ok "INFLUXDB_ORCHESTRATOR_WRITE_TOKEN уже задан — пропускаю"
fi

# ── gateway-read-token: чтение из telemetry + metrics ──────────────────────
if [[ -z "${INFLUXDB_GATEWAY_READ_TOKEN:-}" ]]; then
    GW_READ_TOKEN="$(create_token "gateway-read" \
        "{\"action\":\"read\",\"resource\":{\"type\":\"buckets\",\"id\":\"${TELEMETRY_ID}\",\"orgID\":\"${ORG_ID}\"}}" \
        ",{\"action\":\"read\",\"resource\":{\"type\":\"buckets\",\"id\":\"${METRICS_ID}\",\"orgID\":\"${ORG_ID}\"}}" \
    )" || { log_warn "Не удалось создать gateway-read-token"; GW_READ_TOKEN=""; }
    [[ -n "$GW_READ_TOKEN" ]] && log_ok "gateway-read-token создан: ${GW_READ_TOKEN:0:16}..."
else
    log_ok "INFLUXDB_GATEWAY_READ_TOKEN уже задан — пропускаю"
fi

# ── robot-edge-write-token: запись телеметрии с роботов ────────────────────
if [[ -z "${INFLUXDB_ROBOT_WRITE_TOKEN:-}" ]]; then
    ROBOT_WRITE_TOKEN="$(create_token "robot-edge-write" \
        "{\"action\":\"write\",\"resource\":{\"type\":\"buckets\",\"id\":\"${TELEMETRY_ID}\",\"orgID\":\"${ORG_ID}\"}}" \
    )" || { log_warn "Не удалось создать robot-edge-write-token"; ROBOT_WRITE_TOKEN=""; }
    [[ -n "$ROBOT_WRITE_TOKEN" ]] && log_ok "robot-edge-write-token создан: ${ROBOT_WRITE_TOKEN:0:16}..."
else
    log_ok "INFLUXDB_ROBOT_WRITE_TOKEN уже задан — пропускаю"
fi

# ─── Сводка ──────────────────────────────────────────────────────────────────
echo ""
echo "   InfluxDB инициализирован:"
echo "   ─────────────────────────────────────────────────────────────"
echo "   URL:          ${INFLUX_URL}"
echo "   Org:          ${ORG}  (id=${ORG_ID})"
echo "   Бакеты:       ${BUCKET_TELEMETRY} (90d), metrics (30d), events (7d), audit-logs (365d)"
[[ -n "${ORCH_WRITE_TOKEN:-}" ]] && echo "   Сохраните INFLUXDB_ORCHESTRATOR_WRITE_TOKEN=${ORCH_WRITE_TOKEN}"
[[ -n "${GW_READ_TOKEN:-}"    ]] && echo "   Сохраните INFLUXDB_GATEWAY_READ_TOKEN=${GW_READ_TOKEN}"
[[ -n "${ROBOT_WRITE_TOKEN:-}" ]] && echo "   Сохраните INFLUXDB_ROBOT_WRITE_TOKEN=${ROBOT_WRITE_TOKEN}"
echo "   ─────────────────────────────────────────────────────────────"
