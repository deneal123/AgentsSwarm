#!/usr/bin/env bash
# =============================================================================
# restore.sh — Восстановление баз данных из резервных копий в MinIO
#
# Использование:
#   ./restore.sh --list
#   ./restore.sh --date 2024-01-15_10-00-00 --all
#   ./restore.sh --date 2024-01-15_10-00-00 --postgres
#   ./restore.sh --date 2024-01-15_10-00-00 --influxdb --neo4j
#
# Опции:
#   --list             Показать доступные резервные копии в MinIO
#   --date DATE        Дата бэкапа (формат: YYYY-MM-DD_HH-MM-SS)
#   --latest           Использовать последний доступный бэкап
#   --postgres         Восстановить PostgreSQL
#   --influxdb         Восстановить InfluxDB
#   --neo4j            Восстановить Neo4j
#   --all              Восстановить все БД
#   --yes              Не запрашивать подтверждение (для автоматизации)
#   --dry-run          Показать что будет сделано без выполнения
#   -h, --help         Показать эту справку
#
# ВНИМАНИЕ: Восстановление перезаписывает существующие данные!
#
# Переменные окружения (.env):
#   POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD
#   INFLUXDB_ADMIN_TOKEN, INFLUXDB_ORG
#   NEO4J_AUTH (формат: neo4j/password)
#   MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
# =============================================================================

set -euo pipefail

# ─── Директория скрипта ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

# ─── Цвета ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Лог-функции ─────────────────────────────────────────────────────────────
log()     { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $*"; }
log_ok()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $*"; }
log_err() { echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $*" >&2; }
log_warn(){ echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠${NC} $*"; }
log_hdr() {
  echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${NC}"
  echo -e "${BOLD}${CYAN}  $*${NC}"
  echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}"
}

# ─── Параметры по умолчанию ───────────────────────────────────────────────────
DO_LIST=false
DO_POSTGRES=false
DO_INFLUXDB=false
DO_NEO4J=false
RESTORE_DATE=""
USE_LATEST=false
AUTO_YES=false
DRY_RUN=false

COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
[[ -f "${PROJECT_ROOT}/docker-compose.dev.yml" ]] && COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.dev.yml"

# ─── Результаты для итоговой таблицы ─────────────────────────────────────────
declare -A RESTORE_STATUS

# ─── Разбор аргументов ───────────────────────────────────────────────────────
ANY_DB_SELECTED=false

if [[ $# -eq 0 ]]; then
  sed -n '3,22p' "$0" | sed 's/^# //; s/^#//'
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)     DO_LIST=true ;;
    --date)
      shift
      [[ $# -eq 0 ]] && { log_err "--date требует аргумент"; exit 1; }
      RESTORE_DATE="$1"
      ;;
    --latest)   USE_LATEST=true ;;
    --postgres) DO_POSTGRES=true; ANY_DB_SELECTED=true ;;
    --influxdb) DO_INFLUXDB=true; ANY_DB_SELECTED=true ;;
    --neo4j)    DO_NEO4J=true;    ANY_DB_SELECTED=true ;;
    --all)      DO_POSTGRES=true; DO_INFLUXDB=true; DO_NEO4J=true; ANY_DB_SELECTED=true ;;
    --yes|-y)   AUTO_YES=true ;;
    --dry-run)  DRY_RUN=true ;;
    -h|--help)
      sed -n '3,22p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      log_err "Неизвестный аргумент: $1"
      exit 1
      ;;
  esac
  shift
done

# ─── Загрузка .env ────────────────────────────────────────────────────────────
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  # shellcheck source=/dev/null
  set -o allexport
  source "${PROJECT_ROOT}/.env"
  set +o allexport
fi

# ─── Переменные с дефолтами ──────────────────────────────────────────────────
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-agentsswarm}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
INFLUXDB_TOKEN="${INFLUXDB_ADMIN_TOKEN:-${INFLUXDB_TOKEN:-}}"
INFLUXDB_ORG="${INFLUXDB_ORG:-agentsswarm}"
NEO4J_AUTH="${NEO4J_AUTH:-neo4j/password}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_BUCKET="${MINIO_BUCKET:-agentsswarm}"

# ─── mc wrapper ──────────────────────────────────────────────────────────────
mc_cmd() {
  docker compose -f "${COMPOSE_FILE}" exec -T minio \
    mc --quiet "$@"
}

# Настройка алиаса
setup_mc() {
  mc_cmd alias set agentsswarm "${MINIO_ENDPOINT}" \
    "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" \
    --api S3v4 2>/dev/null || {
    log_err "Не удалось подключиться к MinIO"
    exit 1
  }
}

# ─── Список доступных бэкапов ────────────────────────────────────────────────
list_backups() {
  log_hdr "Доступные резервные копии"

  setup_mc

  echo ""
  echo -e "${BOLD}PostgreSQL:${NC}"
  mc_cmd ls "agentsswarm/backups/postgres/" 2>/dev/null | \
    awk '{print "  " $NF}' | sort -r | head -20 || echo "  (нет бэкапов)"

  echo ""
  echo -e "${BOLD}InfluxDB:${NC}"
  mc_cmd ls "agentsswarm/backups/influxdb/" 2>/dev/null | \
    awk '{print "  " $NF}' | sort -r | head -20 || echo "  (нет бэкапов)"

  echo ""
  echo -e "${BOLD}Neo4j:${NC}"
  mc_cmd ls "agentsswarm/backups/neo4j/" 2>/dev/null | \
    awk '{print "  " $NF}' | sort -r | head -20 || echo "  (нет бэкапов)"

  echo ""
  log "Для восстановления используйте:"
  echo -e "  ${CYAN}./restore.sh --date YYYY-MM-DD_HH-MM-SS --all${NC}"
}

# ─── Найти последний доступный бэкап ─────────────────────────────────────────
find_latest_backup() {
  local db_type="$1"   # postgres | influxdb | neo4j

  mc_cmd ls "agentsswarm/backups/${db_type}/" 2>/dev/null | \
    awk '{print $NF}' | tr -d '/' | sort -r | head -1
}

# ─── Запрос подтверждения ─────────────────────────────────────────────────────
confirm() {
  local prompt="$1"
  if [[ "${AUTO_YES}" == "true" ]]; then
    log_warn "${prompt} (автоматически подтверждено --yes)"
    return 0
  fi
  echo -e "\n${YELLOW}${BOLD}⚠  ВНИМАНИЕ: ${prompt}${NC}"
  echo -e "${YELLOW}   Это действие перезапишет существующие данные!${NC}"
  echo -n "   Продолжить? [y/N] "
  read -r answer
  if [[ "${answer,,}" != "y" && "${answer,,}" != "yes" ]]; then
    log "Отменено пользователем"
    exit 0
  fi
}

# ─── Скачать файл из MinIO на хост ───────────────────────────────────────────
download_from_minio() {
  local remote_path="$1"   # например: backups/postgres/2024-01-01/file.dump
  local local_path="$2"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "  [dry-run] mc cp agentsswarm/${remote_path} → ${local_path}"
    return 0
  fi

  local filename
  filename="$(basename "${remote_path}")"

  log "  Скачивание ← agentsswarm/${remote_path}"
  # mc cp внутри контейнера → /tmp/filename, затем docker cp на хост
  mc_cmd cp "agentsswarm/${remote_path}" "/tmp/${filename}"
  docker compose -f "${COMPOSE_FILE}" cp "minio:/tmp/${filename}" "${local_path}"
  docker compose -f "${COMPOSE_FILE}" exec -T minio \
    rm -f "/tmp/${filename}" 2>/dev/null || true
}

# ─── PostgreSQL restore ───────────────────────────────────────────────────────
restore_postgres() {
  local date_str="$1"

  log_hdr "Восстановление PostgreSQL (${date_str})"

  local remote_file="backups/postgres/${date_str}/${POSTGRES_DB}.dump"
  local local_dump="${TMPDIR_RESTORE}/postgres_restore.dump"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] Скачать ${remote_file} → pg_restore -d ${POSTGRES_DB}"
    RESTORE_STATUS[postgres]="dry-run"
    return 0
  fi

  # Проверяем существование бэкапа
  if ! mc_cmd ls "agentsswarm/${remote_file}" > /dev/null 2>&1; then
    log_err "Файл бэкапа не найден: agentsswarm/${remote_file}"
    log "Доступные даты для postgres:"
    mc_cmd ls "agentsswarm/backups/postgres/" 2>/dev/null | awk '{print "  " $NF}' || true
    RESTORE_STATUS[postgres]="NOT FOUND"
    return 1
  fi

  download_from_minio "${remote_file}" "${local_dump}"
  log_ok "Файл скачан: $(du -sh "${local_dump}" | cut -f1)"

  log "Восстановление в PostgreSQL..."
  # drop connections + restore
  PGPASSWORD="${POSTGRES_PASSWORD}" \
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
      psql -U "${POSTGRES_USER}" -d postgres \
      -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
      > /dev/null 2>&1 || true

  # Пересоздаём БД
  PGPASSWORD="${POSTGRES_PASSWORD}" \
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
      psql -U "${POSTGRES_USER}" -d postgres \
      -c "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";" \
      > /dev/null 2>&1 || true

  PGPASSWORD="${POSTGRES_PASSWORD}" \
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
      psql -U "${POSTGRES_USER}" -d postgres \
      -c "CREATE DATABASE \"${POSTGRES_DB}\" OWNER \"${POSTGRES_USER}\";" \
      > /dev/null 2>&1

  # Копируем дамп в контейнер и запускаем pg_restore
  docker compose -f "${COMPOSE_FILE}" cp "${local_dump}" "postgres:/tmp/restore.dump"
  PGPASSWORD="${POSTGRES_PASSWORD}" \
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
      pg_restore \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --exit-on-error \
        /tmp/restore.dump

  docker compose -f "${COMPOSE_FILE}" exec -T postgres \
    rm -f /tmp/restore.dump 2>/dev/null || true

  RESTORE_STATUS[postgres]="OK"
  log_ok "PostgreSQL восстановлен"
}

# ─── InfluxDB restore ─────────────────────────────────────────────────────────
restore_influxdb() {
  local date_str="$1"

  log_hdr "Восстановление InfluxDB (${date_str})"

  local remote_file="backups/influxdb/${date_str}/influxdb.tar.gz"
  local local_archive="${TMPDIR_RESTORE}/influxdb_restore.tar.gz"
  local local_dir="${TMPDIR_RESTORE}/influx_restore"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] Скачать ${remote_file} → influx restore"
    RESTORE_STATUS[influxdb]="dry-run"
    return 0
  fi

  if ! mc_cmd ls "agentsswarm/${remote_file}" > /dev/null 2>&1; then
    log_err "Файл бэкапа не найден: agentsswarm/${remote_file}"
    RESTORE_STATUS[influxdb]="NOT FOUND"
    return 1
  fi

  download_from_minio "${remote_file}" "${local_archive}"
  log_ok "Архив скачан: $(du -sh "${local_archive}" | cut -f1)"

  log "Распаковка архива..."
  mkdir -p "${local_dir}"
  tar -xzf "${local_archive}" -C "${local_dir}"

  # Находим директорию внутри архива
  local backup_subdir
  backup_subdir=$(find "${local_dir}" -mindepth 1 -maxdepth 1 -type d | head -1)
  [[ -z "${backup_subdir}" ]] && backup_subdir="${local_dir}"

  log "Копирование в контейнер..."
  docker compose -f "${COMPOSE_FILE}" cp "${backup_subdir}" "influxdb:/tmp/influx_restore"

  log "Запуск influx restore..."
  docker compose -f "${COMPOSE_FILE}" exec -T influxdb \
    influx restore /tmp/influx_restore \
      --token "${INFLUXDB_TOKEN}" \
      --host "http://localhost:8086" \
      --full 2>&1

  docker compose -f "${COMPOSE_FILE}" exec -T influxdb \
    rm -rf /tmp/influx_restore 2>/dev/null || true

  RESTORE_STATUS[influxdb]="OK"
  log_ok "InfluxDB восстановлен"
}

# ─── Neo4j restore ────────────────────────────────────────────────────────────
restore_neo4j() {
  local date_str="$1"

  log_hdr "Восстановление Neo4j (${date_str})"

  local neo4j_password
  neo4j_password="${NEO4J_AUTH##*/}"

  local remote_file="backups/neo4j/${date_str}/neo4j.json.gz"
  local local_archive="${TMPDIR_RESTORE}/neo4j_restore.json.gz"
  local local_json="${TMPDIR_RESTORE}/neo4j_restore.json"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] Скачать ${remote_file} → apoc.import.json"
    RESTORE_STATUS[neo4j]="dry-run"
    return 0
  fi

  if ! mc_cmd ls "agentsswarm/${remote_file}" > /dev/null 2>&1; then
    log_err "Файл бэкапа не найден: agentsswarm/${remote_file}"
    RESTORE_STATUS[neo4j]="NOT FOUND"
    return 1
  fi

  # Проверяем APOC
  if ! docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
      cypher-shell -u neo4j -p "${neo4j_password}" --non-interactive \
      "RETURN apoc.version() AS ver" > /dev/null 2>&1; then
    log_warn "APOC недоступен — пропускаем Neo4j restore"
    RESTORE_STATUS[neo4j]="SKIPPED (no APOC)"
    return 0
  fi

  download_from_minio "${remote_file}" "${local_archive}"
  log_ok "Архив скачан: $(du -sh "${local_archive}" | cut -f1)"

  log "Распаковка..."
  gunzip -c "${local_archive}" > "${local_json}"

  log "Копирование JSON в контейнер (/var/lib/neo4j/import/)..."
  docker compose -f "${COMPOSE_FILE}" cp \
    "${local_json}" "neo4j:/var/lib/neo4j/import/restore.json"

  log "Очистка существующих данных..."
  docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
    cypher-shell \
      -u neo4j -p "${neo4j_password}" --non-interactive \
      "MATCH (n) DETACH DELETE n" 2>&1

  log "Импорт через apoc.import.json..."
  if docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
      cypher-shell \
        -u neo4j -p "${neo4j_password}" --non-interactive \
        "CALL apoc.import.json('restore.json')" 2>&1; then
    log_ok "Импорт завершён"
  else
    log_err "apoc.import.json завершился с ошибкой"
    RESTORE_STATUS[neo4j]="FAILED"
    return 1
  fi

  docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
    rm -f /var/lib/neo4j/import/restore.json 2>/dev/null || true

  RESTORE_STATUS[neo4j]="OK"
  log_ok "Neo4j восстановлен"
}

# ─── Итоговая таблица ─────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  printf "${BOLD}${CYAN}║${NC}  RESTORE SUMMARY  •  %-27s${BOLD}${CYAN}║${NC}\n" "${RESTORE_DATE}"
  echo -e "${BOLD}${CYAN}╠══════════════╦═══════════════════════════════════╣${NC}"
  printf "${BOLD}${CYAN}║${NC} %-12s ${BOLD}${CYAN}║${NC} %-33s ${BOLD}${CYAN}║${NC}\n" "База данных" "Статус"
  echo -e "${BOLD}${CYAN}╠══════════════╬═══════════════════════════════════╣${NC}"

  local all_ok=true

  for db in postgres influxdb neo4j; do
    local status="${RESTORE_STATUS[$db]:-SKIPPED}"
    local color="${GREEN}"

    if [[ "${status}" == "FAILED" || "${status}" == "NOT FOUND" ]]; then
      color="${RED}"
      all_ok=false
    elif [[ "${status}" == "SKIPPED"* ]]; then
      color="${YELLOW}"
    elif [[ "${status}" == "dry-run" ]]; then
      color="${CYAN}"
    fi

    printf "${BOLD}${CYAN}║${NC} %-12s ${BOLD}${CYAN}║${NC} ${color}%-33s${NC} ${BOLD}${CYAN}║${NC}\n" \
      "${db}" "${status}"
  done

  echo -e "${BOLD}${CYAN}╚══════════════╩═══════════════════════════════════╝${NC}"
  echo ""

  if [[ "${all_ok}" == "false" ]]; then
    log_err "Один или несколько восстановлений завершились с ошибкой!"
    return 1
  fi
  log_ok "Восстановление завершено"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${NC}"
  echo -e "${BOLD}${CYAN}  AgentsSwarm — Restore${NC}"
  echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}\n"

  # Режим --list
  if [[ "${DO_LIST}" == "true" ]]; then
    list_backups
    exit 0
  fi

  # Нужно хотя бы одна БД для восстановления
  if [[ "${ANY_DB_SELECTED}" == "false" ]]; then
    log_err "Укажите что восстанавливать: --postgres, --influxdb, --neo4j или --all"
    echo -e "  Для просмотра доступных бэкапов: ${CYAN}./restore.sh --list${NC}"
    exit 1
  fi

  # Подключаемся к MinIO
  setup_mc

  # Определяем дату бэкапа
  if [[ "${USE_LATEST}" == "true" && -z "${RESTORE_DATE}" ]]; then
    log "Поиск последнего бэкапа..."
    # Ищем последнюю дату по PostgreSQL (наиболее полный индикатор)
    local latest
    if [[ "${DO_POSTGRES}" == "true" ]]; then
      latest=$(find_latest_backup "postgres")
    elif [[ "${DO_INFLUXDB}" == "true" ]]; then
      latest=$(find_latest_backup "influxdb")
    else
      latest=$(find_latest_backup "neo4j")
    fi

    if [[ -z "${latest}" ]]; then
      log_err "Не найдено ни одного бэкапа в MinIO"
      exit 1
    fi
    RESTORE_DATE="${latest}"
    log_ok "Выбран последний бэкап: ${RESTORE_DATE}"
  fi

  if [[ -z "${RESTORE_DATE}" ]]; then
    log_err "Укажите дату бэкапа через --date YYYY-MM-DD_HH-MM-SS или --latest"
    echo -e "  Для просмотра доступных бэкапов: ${CYAN}./restore.sh --list${NC}"
    exit 1
  fi

  # Запрашиваем подтверждение (если не --yes)
  local targets=""
  [[ "${DO_POSTGRES}" == "true" ]] && targets+="PostgreSQL "
  [[ "${DO_INFLUXDB}" == "true" ]] && targets+="InfluxDB "
  [[ "${DO_NEO4J}" == "true" ]]    && targets+="Neo4j "
  confirm "Восстановить ${targets}из бэкапа ${RESTORE_DATE}?"

  # Создаём временную директорию
  TMPDIR_RESTORE="$(mktemp -d)"
  trap 'log "Очистка временных файлов..."; rm -rf "${TMPDIR_RESTORE}"' EXIT

  log "Временная директория: ${TMPDIR_RESTORE}"
  [[ "${DRY_RUN}" == "true" ]] && log_warn "Режим DRY-RUN — изменения не вносятся"

  # Выполняем восстановление
  [[ "${DO_POSTGRES}" == "true" ]] && restore_postgres "${RESTORE_DATE}" || true
  [[ "${DO_INFLUXDB}" == "true" ]] && restore_influxdb "${RESTORE_DATE}" || true
  [[ "${DO_NEO4J}" == "true" ]]    && restore_neo4j "${RESTORE_DATE}"    || true

  print_summary
}

main "$@"
