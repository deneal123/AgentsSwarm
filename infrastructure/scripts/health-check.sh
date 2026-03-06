#!/usr/bin/env bash
# =============================================================================
# health-check.sh — проверка состояния всех сервисов AgentsSwarm
# =============================================================================

set -euo pipefail

# ─── Цвета ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

OK="${GREEN}✓ OK${NC}"
FAIL="${RED}✗ FAIL${NC}"
SKIP="${YELLOW}~ SKIP${NC}"

PASS=0
ERRORS=0

# ─── Утилиты ──────────────────────────────────────────────────────────────────
check_http() {
    local name="$1"
    local url="$2"
    local expected="${3:-200}"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "$expected" ]]; then
        printf "  ${OK}  %-30s %s\n" "$name" "$url"
        PASS=$(( PASS + 1 ))
    else
        printf "  ${FAIL}  %-30s %s  (HTTP %s)\n" "$name" "$url" "$status"
        ERRORS=$(( ERRORS + 1 ))
    fi
}

check_tcp() {
    local name="$1"
    local host="$2"
    local port="$3"
    if timeout 3 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
        printf "  ${OK}  %-30s %s:%s\n" "$name" "$host" "$port"
        PASS=$(( PASS + 1 ))
    else
        printf "  ${FAIL}  %-30s %s:%s\n" "$name" "$host" "$port"
        ERRORS=$(( ERRORS + 1 ))
    fi
}

# ─── Заголовок ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       AgentsSwarm — Health Check                 ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Application Services ─────────────────────────────────────────────────────
echo -e "${BOLD}  Application Services${NC}"
check_http "GatewayService"       "http://localhost:8005/health"
check_http "GatewayService Ready" "http://localhost:8005/ready"
check_http "Orchestrator Health"  "http://localhost:8006/health"
check_http "vLLM"                 "http://localhost:8003/health"
check_http "Triton HTTP"          "http://localhost:8000/v2/health/ready"
check_http "Frontend"             "http://localhost:3000"
echo ""

# ─── Message Brokers ──────────────────────────────────────────────────────────
echo -e "${BOLD}  Message Brokers${NC}"
check_tcp  "EMQX MQTT"            "localhost" "1883"
check_http "EMQX Dashboard"       "http://localhost:18083"
check_tcp  "RabbitMQ AMQP"        "localhost" "5672"
check_http "RabbitMQ Management"  "http://localhost:15672"
echo ""

# ─── Databases ────────────────────────────────────────────────────────────────
echo -e "${BOLD}  Databases${NC}"
check_tcp  "PostgreSQL"           "localhost" "5432"
check_http "InfluxDB"             "http://localhost:8086/health"
check_http "Neo4j Browser"        "http://localhost:7474"
check_tcp  "Redis"                "localhost" "6379"
check_http "Redis Insight"        "http://localhost:8001"
check_http "MinIO API"            "http://localhost:9000/minio/health/live"
check_http "MinIO Console"        "http://localhost:9001"
echo ""

# ─── Итог ─────────────────────────────────────────────────────────────────────
echo -e "${BOLD}  Итог${NC}"
TOTAL=$(( PASS + ERRORS ))
if [[ $ERRORS -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}✅  Все сервисы в норме ($PASS/$TOTAL)${NC}"
else
    echo -e "  ${RED}${BOLD}❌  Обнаружены проблемы: $ERRORS из $TOTAL сервисов недоступны${NC}"
fi
echo ""

exit $ERRORS
