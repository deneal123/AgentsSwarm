#!/usr/bin/env bash
# =============================================================================
# curl_tests.sh — ручная проверка всех HTTP-роутов pushi-backend
#
# Использование:
#   BASE_URL=http://localhost:8002 bash tests/curl_tests.sh
#   или просто:
#   bash tests/curl_tests.sh          # по умолчанию localhost:8002
#
# Переменные окружения:
#   BASE_URL    — базовый URL (default: http://localhost:8002)
#   EMAIL       — email тестового пользователя (default: testcurl@example.com)
#   PASSWORD    — пароль (default: CurlTest123!)
#   VERBOSE     — 1 = выводить тела ответов (default: 0)
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8002}"
EMAIL="${EMAIL:-testcurl@example.com}"
PASSWORD="${PASSWORD:-CurlTest123!}"
VERBOSE="${VERBOSE:-0}"
COOKIE_JAR="/tmp/pushi_curl_cookies.txt"

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
RESET="\033[0m"

PASS=0
FAIL=0

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

check() {
    local name="$1"
    local expected_status="$2"
    local actual_status="$3"
    local body="$4"

    if [ "$actual_status" = "$expected_status" ]; then
        echo -e "${GREEN}[PASS]${RESET} ${name}  (HTTP ${actual_status})"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}[FAIL]${RESET} ${name}  (expected ${expected_status}, got ${actual_status})"
        [ "$VERBOSE" = "1" ] && echo "       body: ${body}"
        FAIL=$((FAIL + 1))
    fi
}

check_any() {
    # pass if actual_status is in space-separated list of accepted codes
    local name="$1"
    local accepted="$2"   # e.g. "200 201"
    local actual_status="$3"
    local body="$4"

    for code in $accepted; do
        if [ "$actual_status" = "$code" ]; then
            echo -e "${GREEN}[PASS]${RESET} ${name}  (HTTP ${actual_status})"
            PASS=$((PASS + 1))
            return 0
        fi
    done
    echo -e "${RED}[FAIL]${RESET} ${name}  (expected one of [${accepted}], got ${actual_status})"
    [ "$VERBOSE" = "1" ] && echo "       body: ${body}"
    FAIL=$((FAIL + 1))
}

curl_json() {
    # Returns HTTP status code; writes response body to $BODY
    BODY=$(curl -s -o /tmp/pushi_curl_resp.txt -w "%{http_code}" \
        -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        -H "Content-Type: application/json" \
        "$@")
    BODY_CONTENT=$(cat /tmp/pushi_curl_resp.txt 2>/dev/null || echo "")
}

curl_form() {
    BODY=$(curl -s -o /tmp/pushi_curl_resp.txt -w "%{http_code}" \
        -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        "$@")
    BODY_CONTENT=$(cat /tmp/pushi_curl_resp.txt 2>/dev/null || echo "")
}

# --------------------------------------------------------------------------
# Pre-flight: service availability
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}=== pushi-backend curl smoke tests ===${RESET}"
echo "BASE_URL : $BASE_URL"
echo "EMAIL    : $EMAIL"
echo ""

rm -f "$COOKIE_JAR"

# Health check
curl_json "$BASE_URL/api/health"
check "GET /api/health" "200" "$BODY"

curl_json "$BASE_URL/"
check "GET / (root)" "200" "$BODY"

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Auth ---${RESET}"

# Register (может вернуть 400 если пользователь уже существует — это ок)
curl_json -X POST "$BASE_URL/api/v1/auth/register" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"first_name\":\"Curl\",\"last_name\":\"Test\"}"
check_any "POST /api/v1/auth/register" "200 201 400" "$BODY"

# Login
curl_json -X POST "$BASE_URL/api/v1/auth/login" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
check "POST /api/v1/auth/login" "200" "$BODY"

# Сохраняем access_token из ответа
ACCESS_TOKEN=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")
REFRESH_TOKEN=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refresh_token',''))" 2>/dev/null || echo "")

# Refresh token
if [ -n "$REFRESH_TOKEN" ]; then
    curl_json -X POST "$BASE_URL/api/v1/auth/refresh" \
        -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
    check "POST /api/v1/auth/refresh" "200" "$BODY"
else
    echo -e "${YELLOW}[SKIP]${RESET} POST /api/v1/auth/refresh  (no refresh_token)"
fi

# Guest session
curl_json -X POST "$BASE_URL/api/v1/auth/guest"
check_any "POST /api/v1/auth/guest" "200 201" "$BODY"
GUEST_TOKEN=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('guest_token',''))" 2>/dev/null || echo "")

# Logout
curl_json -X POST "$BASE_URL/api/v1/auth/logout"
check "POST /api/v1/auth/logout" "200" "$BODY"

# Re-login so subsequent requests are authenticated
curl_json -X POST "$BASE_URL/api/v1/auth/login" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
# Cookie is set automatically via COOKIE_JAR

# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Profile ---${RESET}"

curl_json "$BASE_URL/api/v1/profile/me"
check "GET /api/v1/profile/me" "200" "$BODY"

curl_json -X PATCH "$BASE_URL/api/v1/profile/me" \
    -d "{\"first_name\":\"CurlUpdated\"}"
check "PATCH /api/v1/profile/me" "200" "$BODY"

# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Rules ---${RESET}"

curl_json "$BASE_URL/api/v1/rules"
check "GET /api/v1/rules" "200" "$BODY"

curl_json "$BASE_URL/api/v1/rules/snapshot"
check "GET /api/v1/rules/snapshot" "200" "$BODY"

# Create rule (admin required — may return 403 for non-admin)
curl_json -X POST "$BASE_URL/api/v1/rules" \
    -d '{"name":"Curl Rule","description":"test","rule_type":"simple","product_type":"all","channel_type":"all","is_active":true}'
check_any "POST /api/v1/rules" "200 201 403" "$BODY"

RULE_ID=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

if [ -n "$RULE_ID" ]; then
    curl_json "$BASE_URL/api/v1/rules/$RULE_ID"
    check "GET /api/v1/rules/{id}" "200" "$BODY"

    curl_json "$BASE_URL/api/v1/rules/$RULE_ID/versions"
    check "GET /api/v1/rules/{id}/versions" "200" "$BODY"

    curl_json -X PUT "$BASE_URL/api/v1/rules/$RULE_ID" \
        -d '{"name":"Updated Curl Rule"}'
    check "PUT /api/v1/rules/{id}" "200" "$BODY"

    curl_json -X POST "$BASE_URL/api/v1/rules/$RULE_ID/versions" \
        -d '{"content":"rule: text contains Купи","description":"v2"}'
    check_any "POST /api/v1/rules/{id}/versions" "200 201" "$BODY"

    curl_json "$BASE_URL/api/v1/rules/$RULE_ID/preference"
    check_any "GET /api/v1/rules/{id}/preference" "200 404" "$BODY"

    curl_json -X PATCH "$BASE_URL/api/v1/rules/$RULE_ID/preference" \
        -d '{"active_version_id":null}'
    check_any "PATCH /api/v1/rules/{id}/preference" "200 422" "$BODY"

    curl_json -X DELETE "$BASE_URL/api/v1/rules/$RULE_ID"
    check_any "DELETE /api/v1/rules/{id}" "200 204 403" "$BODY"
else
    echo -e "${YELLOW}[SKIP]${RESET} Rule sub-tests (rule not created, likely 403 — admin required)"
fi

# Import rules (file upload, admin only)
curl_form -X POST "$BASE_URL/api/v1/rules/import" \
    -F "file=@/dev/null;filename=rules.toml;type=application/toml"
check_any "POST /api/v1/rules/import" "200 403 422" "$BODY"

# Pipeline configs
curl_json "$BASE_URL/api/v1/rules/pipeline-configs"
check_any "GET /api/v1/rules/pipeline-configs" "200 403" "$BODY"

curl_json -X POST "$BASE_URL/api/v1/rules/pipeline-configs" \
    -d '{"name":"Default","config":{}}'
check_any "POST /api/v1/rules/pipeline-configs" "200 201 403" "$BODY"

# --------------------------------------------------------------------------
# Playground
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Playground ---${RESET}"

curl_json -X POST "$BASE_URL/api/v1/playground/analyze" \
    -d '{"communications":[{"text":"Купи кредит!","type":"sms"}]}'
check_any "POST /api/v1/playground/analyze" "200 202" "$BODY"
PLAYGROUND_TASK_ID=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

if [ -n "$PLAYGROUND_TASK_ID" ]; then
    curl_json "$BASE_URL/api/v1/playground/tasks/$PLAYGROUND_TASK_ID"
    check_any "GET /api/v1/playground/tasks/{id}" "200 404" "$BODY"

    curl_json "$BASE_URL/api/v1/playground/results/$PLAYGROUND_TASK_ID"
    check_any "GET /api/v1/playground/results/{id}" "200 404" "$BODY"

    curl_json -X DELETE "$BASE_URL/api/v1/playground/tasks/$PLAYGROUND_TASK_ID"
    check_any "DELETE /api/v1/playground/tasks/{id}" "200 404" "$BODY"
else
    echo -e "${YELLOW}[SKIP]${RESET} Playground sub-tests (no task_id in response)"
fi

curl_json "$BASE_URL/api/v1/playground/tasks"
check "GET /api/v1/playground/tasks" "200" "$BODY"

# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Pipeline ---${RESET}"

# dataset_id is a query param — using a dummy UUID
DUMMY_UUID="00000000-0000-0000-0000-000000000001"

curl_json -X POST "$BASE_URL/api/v1/pipeline/run?dataset_id=$DUMMY_UUID"
check_any "POST /api/v1/pipeline/run" "200 202 404 422" "$BODY"
PIPELINE_TASK_ID=$(echo "$BODY_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

curl_json "$BASE_URL/api/v1/pipeline/reports"
check "GET /api/v1/pipeline/reports" "200" "$BODY"

if [ -n "$PIPELINE_TASK_ID" ]; then
    curl_json "$BASE_URL/api/v1/pipeline/reports/$PIPELINE_TASK_ID"
    check_any "GET /api/v1/pipeline/reports/{id}" "200 404" "$BODY"

    curl_json "$BASE_URL/api/v1/pipeline/tasks/$PIPELINE_TASK_ID"
    check_any "GET /api/v1/pipeline/tasks/{id}" "200 404" "$BODY"

    curl_json -X DELETE "$BASE_URL/api/v1/pipeline/tasks/$PIPELINE_TASK_ID"
    check_any "DELETE /api/v1/pipeline/tasks/{id}" "200 404" "$BODY"
else
    echo -e "${YELLOW}[SKIP]${RESET} Pipeline sub-tests (no task_id)"
fi

# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Files ---${RESET}"

curl_form -X POST "$BASE_URL/api/v1/files/config" \
    -F "file=@/dev/null;filename=config.yaml;type=application/x-yaml"
check_any "POST /api/v1/files/config" "200 202 400 422" "$BODY"

curl_form -X POST "$BASE_URL/api/v1/files/dataset" \
    -F "file=@/dev/null;filename=data.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
check_any "POST /api/v1/files/dataset" "200 202 400 422" "$BODY"

# --------------------------------------------------------------------------
# Communication Results
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}--- Communication Results ---${RESET}"

curl_json "$BASE_URL/api/v1/communications/$DUMMY_UUID/results"
check_any "GET /api/v1/communications/{task_id}/results" "200 404" "$BODY"

curl_json "$BASE_URL/api/v1/communications/$DUMMY_UUID/stats"
check_any "GET /api/v1/communications/{task_id}/stats" "200 404" "$BODY"

curl_json "$BASE_URL/api/v1/communications/items/$DUMMY_UUID"
check_any "GET /api/v1/communications/items/{comm_id}" "200 404" "$BODY"

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

echo ""
echo -e "${YELLOW}=== Summary ===${RESET}"
echo -e "  ${GREEN}Passed: $PASS${RESET}"
if [ "$FAIL" -gt 0 ]; then
    echo -e "  ${RED}Failed: $FAIL${RESET}"
    exit 1
else
    echo -e "  Failed: $FAIL"
    echo -e "${GREEN}All checks passed!${RESET}"
fi
