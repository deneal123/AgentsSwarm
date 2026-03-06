#!/usr/bin/env bash
# =============================================================================
# infrastructure/minio/init.sh
# Инициализация MinIO: бакеты, политики доступа, версионирование, lifecycle.
#
# Зависимости: mc (MinIO Client) — установлен в образе minio/mc или
#   доступен через docker compose exec -T minio mc ...
#
# Переменные окружения:
#   MINIO_URL             — URL MinIO (по умолчанию: http://localhost:9000)
#   MINIO_ROOT_USER       — логин root (по умолчанию: minioadmin)
#   MINIO_ROOT_PASSWORD   — пароль root (по умолчанию: minioadmin)
#   COMPOSE_FILE          — путь до docker-compose.dev.yml (задаётся автоматически)
# =============================================================================

set -euo pipefail

MINIO_URL="${MINIO_URL:-http://localhost:9000}"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minio_secret}"
ALIAS="agentsswarm"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_ok()   { echo -e "   ${GREEN}✓${NC}  $*"; }
log_warn() { echo -e "   ${YELLOW}⚠${NC}  $*"; }
log_err()  { echo -e "   ${RED}✗${NC}  $*"; }

# ─── Проверка наличия mc ───────────────────────────────────────────────────────
if ! command -v mc &> /dev/null; then
    log_err "mc (MinIO Client) не найден в PATH"
    log_warn "Установка через: curl -Lo /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x /usr/local/bin/mc"
    exit 1
fi

# ─── Ожидание готовности MinIO ────────────────────────────────────────────────
echo "▶  Ожидание готовности MinIO (${MINIO_URL})..."
MAX_WAIT=60
ELAPSED=0
until curl -sf "${MINIO_URL}/minio/health/live" > /dev/null 2>&1; do
    if [[ $ELAPSED -ge $MAX_WAIT ]]; then
        log_err "MinIO не отвечает через ${MAX_WAIT}s — прерываю"
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
log_ok "MinIO доступен (${ELAPSED}s)"

# ─── Настройка алиаса ─────────────────────────────────────────────────────────
mc alias set "${ALIAS}" "${MINIO_URL}" "${MINIO_USER}" "${MINIO_PASS}" --api S3v4 > /dev/null
log_ok "Алиас '${ALIAS}' настроен"

# ─── Вспомогательные функции ──────────────────────────────────────────────────
bucket_exists() {
    mc ls "${ALIAS}/$1" > /dev/null 2>&1
}

create_bucket_if_missing() {
    local bucket="$1"
    if bucket_exists "$bucket"; then
        log_ok "Бакет '${bucket}' уже существует"
    else
        mc mb "${ALIAS}/${bucket}" > /dev/null
        log_ok "Бакет '${bucket}' создан"
    fi
}

# ─── Создание бакетов ─────────────────────────────────────────────────────────
echo "▶  Создание бакетов..."
create_bucket_if_missing "models"
create_bucket_if_missing "datasets"
create_bucket_if_missing "rosbags"
create_bucket_if_missing "videos"
create_bucket_if_missing "maps"
create_bucket_if_missing "snapshots"
create_bucket_if_missing "audit-logs"

# ─── Версионирование ──────────────────────────────────────────────────────────
echo "▶  Настройка версионирования..."
mc version enable "${ALIAS}/models"   > /dev/null && log_ok "Версионирование: models"
mc version enable "${ALIAS}/datasets" > /dev/null && log_ok "Версионирование: datasets"

# ─── Политики доступа ─────────────────────────────────────────────────────────
echo "▶  Настройка политик доступа..."

# models, datasets — download (анонимный read, authenticated write)
mc anonymous set download "${ALIAS}/models"   > /dev/null && log_ok "Policy download: models"
mc anonymous set download "${ALIAS}/datasets" > /dev/null && log_ok "Policy download: datasets"

# остальные — private (только аутентифицированный доступ)
for bucket in rosbags videos maps snapshots audit-logs; do
    mc anonymous set private "${ALIAS}/${bucket}" > /dev/null && log_ok "Policy private: ${bucket}"
done

# ─── Lifecycle rules ─────────────────────────────────────────────────────────
echo "▶  Настройка lifecycle rules..."

# rosbags — удалять через 90 дней
mc ilm rule add \
    --expire-days 90 \
    --prefix "" \
    "${ALIAS}/rosbags" > /dev/null && log_ok "Lifecycle rosbags: expire 90d"

# videos — удалять через 30 дней
mc ilm rule add \
    --expire-days 30 \
    --prefix "" \
    "${ALIAS}/videos" > /dev/null && log_ok "Lifecycle videos: expire 30d"

# snapshots — удалять через 7 дней
mc ilm rule add \
    --expire-days 7 \
    --prefix "" \
    "${ALIAS}/snapshots" > /dev/null && log_ok "Lifecycle snapshots: expire 7d"

# audit-logs — удалять через 365 дней
mc ilm rule add \
    --expire-days 365 \
    --prefix "" \
    "${ALIAS}/audit-logs" > /dev/null && log_ok "Lifecycle audit-logs: expire 365d"

# ─── Сервисные аккаунты ───────────────────────────────────────────────────────
echo "▶  Создание сервисных аккаунтов..."

# orchestrator-svc: полный доступ к models, datasets, rosbags, audit-logs
ORCH_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::models/*",   "arn:aws:s3:::models",
        "arn:aws:s3:::datasets/*", "arn:aws:s3:::datasets",
        "arn:aws:s3:::rosbags/*",  "arn:aws:s3:::rosbags",
        "arn:aws:s3:::audit-logs/*","arn:aws:s3:::audit-logs"
      ]
    }
  ]
}'

# gateway-svc: чтение models/maps, запись videos/snapshots/audit-logs
GW_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::models/*",   "arn:aws:s3:::models",
        "arn:aws:s3:::maps/*",     "arn:aws:s3:::maps"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:GetObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::videos/*",      "arn:aws:s3:::videos",
        "arn:aws:s3:::snapshots/*",   "arn:aws:s3:::snapshots",
        "arn:aws:s3:::audit-logs/*",  "arn:aws:s3:::audit-logs"
      ]
    }
  ]
}'

# Создаём политики
echo "${ORCH_POLICY}" | mc admin policy create "${ALIAS}" orchestrator-policy /dev/stdin > /dev/null \
    && log_ok "Политика 'orchestrator-policy' создана" \
    || log_warn "Политика 'orchestrator-policy' уже существует — пропускаю"

echo "${GW_POLICY}" | mc admin policy create "${ALIAS}" gateway-policy /dev/stdin > /dev/null \
    && log_ok "Политика 'gateway-policy' создана" \
    || log_warn "Политика 'gateway-policy' уже существует — пропускаю"

# Создаём сервисные аккаунты (access key / secret key)
ORCH_CREDS="$(mc admin user svcacct add \
    --access-key "orchestrator-svc" \
    --secret-key "${MINIO_ROOT_PASSWORD:-minio_secret}_orch" \
    "${ALIAS}" "${MINIO_USER}" 2>&1)" \
    && log_ok "Сервисный аккаунт orchestrator-svc создан" \
    || log_warn "Сервисный аккаунт orchestrator-svc уже существует — пропускаю"

GW_CREDS="$(mc admin user svcacct add \
    --access-key "gateway-svc" \
    --secret-key "${MINIO_ROOT_PASSWORD:-minio_secret}_gw" \
    "${ALIAS}" "${MINIO_USER}" 2>&1)" \
    && log_ok "Сервисный аккаунт gateway-svc создан" \
    || log_warn "Сервисный аккаунт gateway-svc уже существует — пропускаю"

# ─── Сводка ───────────────────────────────────────────────────────────────────
echo ""
echo "   MinIO инициализирован:"
echo "   ─────────────────────────────────────────────────────────────"
echo "   URL:       ${MINIO_URL}"
echo "   Console:   ${MINIO_URL/:9000/:9001}"
echo "   Бакеты:    models, datasets, rosbags, videos, maps, snapshots, audit-logs"
echo "   ─────────────────────────────────────────────────────────────"
echo "   Доступ к консоли: ${MINIO_USER} / ${MINIO_PASS}"
