#!/usr/bin/env bash
# =============================================================================
# backup.sh — Резервное копирование всех БД в MinIO
#
# Использование:
#   ./backup.sh [ОПЦИИ]
#
# Опции:
#   --postgres     Резервная копия только PostgreSQL
#   --influxdb     Резервная копия только InfluxDB
#   --neo4j        Резервная копия только Neo4j
#   --all          Резервная копия всех БД (по умолчанию)
#   --no-retention Не удалять старые бэкапы
#   --dry-run      Только показать что будет сделано, без выполнения
#   -h, --help     Показать эту справку
#
# Переменные окружения (.env):
#   POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD
#   INFLUXDB_ADMIN_TOKEN, INFLUXDB_ORG
#   NEO4J_AUTH (формат: neo4j/password)
#   MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
#   BACKUP_RETENTION_DAYS (по умолчанию: 30)
# =============================================================================

set -euo pipefail

# ─── Директория скрипта (работаем всегда из корня проекта) ───────────────────
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
DO_POSTGRES=false
DO_INFLUXDB=false
DO_NEO4J=false
DO_RETENTION=true
DRY_RUN=false

# Определяем compose файл (dev имеет приоритет)
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
[[ -f "${PROJECT_ROOT}/docker-compose.dev.yml" ]] && COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.dev.yml"

# ─── Результаты для итоговой таблицы ─────────────────────────────────────────
declare -A BACKUP_STATUS
declare -A BACKUP_SIZE

# ─── Разбор аргументов ───────────────────────────────────────────────────────
ANY_SELECTED=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --postgres)     DO_POSTGRES=true; ANY_SELECTED=true ;;
    --influxdb)     DO_INFLUXDB=true; ANY_SELECTED=true ;;
    --neo4j)        DO_NEO4J=true;    ANY_SELECTED=true ;;
    --all)          DO_POSTGRES=true; DO_INFLUXDB=true; DO_NEO4J=true; ANY_SELECTED=true ;;
    --no-retention) DO_RETENTION=false ;;
    --dry-run)      DRY_RUN=true ;;
    -h|--help)
      sed -n '3,23p' "$0" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      log_err "Неизвестный аргумент: $1"
      exit 1
      ;;
  esac
  shift
done

# Без аргументов — бэкапим всё
if [[ "${ANY_SELECTED}" == "false" ]]; then
  DO_POSTGRES=true
  DO_INFLUXDB=true
  DO_NEO4J=true
fi

# ─── Загрузка .env ────────────────────────────────────────────────────────────
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  # shellcheck source=/dev/null
  set -o allexport
  source "${PROJECT_ROOT}/.env"
  set +o allexport
else
  log_warn ".env файл не найден, используются переменные окружения"
fi

# ─── Значения переменных (с дефолтами) ───────────────────────────────────────
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
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# ─── Дата и временная директория ─────────────────────────────────────────────
DATE="$(date '+%Y-%m-%d_%H-%M-%S')"
TMPDIR_BACKUP="$(mktemp -d)"
# Всегда удаляем TMPDIR при выходе (даже при ошибке)
trap 'log "Очистка временных файлов..."; rm -rf "${TMPDIR_BACKUP}"' EXIT

log_hdr "AgentsSwarm Backup  •  ${DATE}"
log "Временная директория: ${TMPDIR_BACKUP}"
log "Compose файл:         ${COMPOSE_FILE}"
[[ "${DRY_RUN}" == "true" ]] && log_warn "Режим DRY-RUN — изменения не вносятся"

# ─── Вспомогательные функции ─────────────────────────────────────────────────

# Запуск mc (MinIO Client) внутри контейнера minio
mc_cmd() {
  docker compose -f "${COMPOSE_FILE}" exec -T minio \
    mc --quiet "$@"
}

# Настройка алиаса MinIO Client
setup_mc() {
  log "Настройка mc alias..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    log "  [dry-run] mc alias set agentsswarm ${MINIO_ENDPOINT} *** ***"
    return 0
  fi
  mc_cmd alias set agentsswarm "${MINIO_ENDPOINT}" \
    "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" \
    --api S3v4 2>/dev/null || {
    log_err "Не удалось настроить mc alias — MinIO недоступен?"
    return 1
  }
  log_ok "mc alias настроен"
}

# Загрузка файла в MinIO
# Аргументы: <локальный_путь> <путь_в_бакете>
upload_to_minio() {
  local local_path="$1"
  local remote_path="$2"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "  [dry-run] upload ${local_path} → agentsswarm/${remote_path}"
    return 0
  fi

  local filename
  filename="$(basename "${local_path}")"

  log "  Загрузка → agentsswarm/${remote_path}"
  # Копируем файл в контейнер minio через docker cp, затем mc cp внутри
  docker compose -f "${COMPOSE_FILE}" cp "${local_path}" "minio:/tmp/${filename}"
  mc_cmd cp "/tmp/${filename}" "agentsswarm/${remote_path}"
  # Удаляем временный файл из контейнера
  docker compose -f "${COMPOSE_FILE}" exec -T minio \
    rm -f "/tmp/${filename}" 2>/dev/null || true
}

# Человекочитаемый размер файла
human_size() {
  local f="$1"
  if [[ -f "${f}" ]]; then
    du -sh "${f}" | cut -f1
  else
    echo "—"
  fi
}

# ─── PostgreSQL backup ────────────────────────────────────────────────────────
backup_postgres() {
  log_hdr "PostgreSQL → MinIO"

  local dump_file="${TMPDIR_BACKUP}/postgres_${DATE}.dump"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] pg_dump -Fc ${POSTGRES_DB} > ${dump_file}"
    BACKUP_STATUS[postgres]="dry-run"
    BACKUP_SIZE[postgres]="—"
    return 0
  fi

  log "Создание дампа (формат custom, со встроенным сжатием)..."
  if PGPASSWORD="${POSTGRES_PASSWORD}" \
    docker compose -f "${COMPOSE_FILE}" exec -T postgres \
      pg_dump \
        -U "${POSTGRES_USER}" \
        -Fc \
        --no-password \
        "${POSTGRES_DB}" > "${dump_file}"; then
    log_ok "Дамп создан: $(human_size "${dump_file}")"
  else
    log_err "pg_dump завершился с ошибкой"
    BACKUP_STATUS[postgres]="FAILED"
    BACKUP_SIZE[postgres]="—"
    return 1
  fi

  upload_to_minio "${dump_file}" "backups/postgres/${DATE}/${POSTGRES_DB}.dump"

  BACKUP_STATUS[postgres]="OK"
  BACKUP_SIZE[postgres]="$(human_size "${dump_file}")"
  log_ok "PostgreSQL backup завершён"
}

# ─── InfluxDB backup ──────────────────────────────────────────────────────────
backup_influxdb() {
  log_hdr "InfluxDB → MinIO"

  local influx_tmp_path="/tmp/influx_backup_${DATE}"
  local influx_local="${TMPDIR_BACKUP}/influx_backup"
  local influx_archive="${TMPDIR_BACKUP}/influxdb_${DATE}.tar.gz"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] influx backup ${influx_tmp_path} --token ***"
    BACKUP_STATUS[influxdb]="dry-run"
    BACKUP_SIZE[influxdb]="—"
    return 0
  fi

  log "Запуск influx backup внутри контейнера..."
  if docker compose -f "${COMPOSE_FILE}" exec -T influxdb \
      influx backup "${influx_tmp_path}" \
        --token "${INFLUXDB_TOKEN}" \
        --host "http://localhost:8086" 2>&1; then
    log_ok "influx backup завершён"
  else
    log_err "influx backup завершился с ошибкой"
    BACKUP_STATUS[influxdb]="FAILED"
    BACKUP_SIZE[influxdb]="—"
    return 1
  fi

  # Копируем директорию backup из контейнера на хост
  log "Копирование из контейнера..."
  docker compose -f "${COMPOSE_FILE}" cp \
    "influxdb:${influx_tmp_path}" \
    "${influx_local}"

  # Удаляем временный backup внутри контейнера
  docker compose -f "${COMPOSE_FILE}" exec -T influxdb \
    rm -rf "${influx_tmp_path}" 2>/dev/null || true

  # Архивируем
  log "Архивирование..."
  tar -czf "${influx_archive}" -C "$(dirname "${influx_local}")" "$(basename "${influx_local}")"

  log_ok "Архив: $(human_size "${influx_archive}")"

  upload_to_minio "${influx_archive}" "backups/influxdb/${DATE}/influxdb.tar.gz"

  BACKUP_STATUS[influxdb]="OK"
  BACKUP_SIZE[influxdb]="$(human_size "${influx_archive}")"
  log_ok "InfluxDB backup завершён"
}

# ─── Neo4j backup (через APOC export) ────────────────────────────────────────
# Community Edition не поддерживает neo4j-admin dump на работающем экземпляре.
# Используем APOC apoc.export.json.all → /var/lib/neo4j/import/
backup_neo4j() {
  log_hdr "Neo4j → MinIO (via APOC)"

  local neo4j_password
  neo4j_password="${NEO4J_AUTH##*/}"   # "neo4j/password" → "password"

  local export_filename="neo4j_backup_${DATE}.json"
  local export_in_container="/var/lib/neo4j/import/${export_filename}"
  local export_local="${TMPDIR_BACKUP}/${export_filename}"
  local export_archive="${TMPDIR_BACKUP}/neo4j_${DATE}.json.gz"

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] CALL apoc.export.json.all('${export_filename}', {})"
    BACKUP_STATUS[neo4j]="dry-run"
    BACKUP_SIZE[neo4j]="—"
    return 0
  fi

  # Проверяем что APOC доступен
  log "Проверка доступности APOC..."
  if ! docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
      cypher-shell \
        -u neo4j \
        -p "${neo4j_password}" \
        --non-interactive \
        "RETURN apoc.version() AS ver" > /dev/null 2>&1; then
    log_warn "APOC недоступен — пропускаем Neo4j backup"
    log_warn "Для включения APOC добавьте NEO4J_PLUGINS=[\\\"apoc\\\"] в docker-compose"
    BACKUP_STATUS[neo4j]="SKIPPED (no APOC)"
    BACKUP_SIZE[neo4j]="—"
    return 0
  fi
  log_ok "APOC доступен"

  log "Экспорт графа через apoc.export.json.all..."
  if docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
      cypher-shell \
        -u neo4j \
        -p "${neo4j_password}" \
        --non-interactive \
        "CALL apoc.export.json.all('${export_filename}', {useTypes: true, storeNodeIds: false})" 2>&1; then
    log_ok "Экспорт завершён"
  else
    log_err "apoc.export.json.all завершился с ошибкой"
    BACKUP_STATUS[neo4j]="FAILED"
    BACKUP_SIZE[neo4j]="—"
    return 1
  fi

  # Копируем из контейнера
  log "Копирование файла из контейнера..."
  docker compose -f "${COMPOSE_FILE}" cp \
    "neo4j:${export_in_container}" \
    "${export_local}"

  # Удаляем временный файл в контейнере
  docker compose -f "${COMPOSE_FILE}" exec -T neo4j \
    rm -f "${export_in_container}" 2>/dev/null || true

  # Сжимаем
  gzip -c "${export_local}" > "${export_archive}"

  log_ok "Архив: $(human_size "${export_archive}")"

  upload_to_minio "${export_archive}" "backups/neo4j/${DATE}/neo4j.json.gz"

  BACKUP_STATUS[neo4j]="OK"
  BACKUP_SIZE[neo4j]="$(human_size "${export_archive}")"
  log_ok "Neo4j backup завершён"
}

# ─── Retention — удаление старых бэкапов ────────────────────────────────────
apply_retention() {
  log_hdr "Retention Policy (>${BACKUP_RETENTION_DAYS} дней)"

  local retention_hours=$(( BACKUP_RETENTION_DAYS * 24 ))

  if [[ "${DRY_RUN}" == "true" ]]; then
    log "[dry-run] mc find agentsswarm/backups --older-than ${retention_hours}h --exec 'mc rm --force {}'"
    return 0
  fi

  # Считаем сколько объектов попадают под очистку
  local old_objects
  old_objects=$(mc_cmd find "agentsswarm/backups" \
    --older-than "${retention_hours}h" 2>/dev/null || true)

  local old_count
  old_count=$(echo "${old_objects}" | grep -c . 2>/dev/null || echo "0")

  if [[ "${old_count}" -eq 0 ]]; then
    log_ok "Старых бэкапов нет"
    return 0
  fi

  log "Объектов старше ${BACKUP_RETENTION_DAYS} дней: ${old_count}"
  log "Удаление..."

  # Удаляем каждый объект через mc rm
  echo "${old_objects}" | while IFS= read -r obj; do
    [[ -z "${obj}" ]] && continue
    mc_cmd rm --force "${obj}" 2>/dev/null && log "  Удалён: ${obj}" || true
  done

  log_ok "Retention policy применена"
}

# ─── Итоговая таблица ─────────────────────────────────────────────────────────
print_summary() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  printf "${BOLD}${CYAN}║${NC}  BACKUP SUMMARY  •  %-28s${BOLD}${CYAN}║${NC}\n" "${DATE}"
  echo -e "${BOLD}${CYAN}╠══════════════╦══════════════════╦════════════════╣${NC}"
  printf "${BOLD}${CYAN}║${NC} %-12s ${BOLD}${CYAN}║${NC} %-16s ${BOLD}${CYAN}║${NC} %-14s ${BOLD}${CYAN}║${NC}\n" \
    "База данных" "Статус" "Размер"
  echo -e "${BOLD}${CYAN}╠══════════════╬══════════════════╬════════════════╣${NC}"

  local all_ok=true

  for db in postgres influxdb neo4j; do
    local status="${BACKUP_STATUS[$db]:-SKIPPED}"
    local size="${BACKUP_SIZE[$db]:-—}"
    local color="${GREEN}"

    if [[ "${status}" == "FAILED" ]]; then
      color="${RED}"
      all_ok=false
    elif [[ "${status}" == "SKIPPED"* ]]; then
      color="${YELLOW}"
    elif [[ "${status}" == "dry-run" ]]; then
      color="${CYAN}"
    fi

    printf "${BOLD}${CYAN}║${NC} %-12s ${BOLD}${CYAN}║${NC} ${color}%-16s${NC} ${BOLD}${CYAN}║${NC} %-14s ${BOLD}${CYAN}║${NC}\n" \
      "${db}" "${status}" "${size}"
  done

  echo -e "${BOLD}${CYAN}╚══════════════╩══════════════════╩════════════════╝${NC}"
  echo ""

  if [[ "${all_ok}" == "false" ]]; then
    log_err "Один или несколько бэкапов завершились с ошибкой!"
    return 1
  fi
  log_ok "Все бэкапы успешно завершены"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  setup_mc

  [[ "${DO_POSTGRES}" == "true" ]] && backup_postgres || true
  [[ "${DO_INFLUXDB}" == "true" ]] && backup_influxdb || true
  [[ "${DO_NEO4J}" == "true" ]]    && backup_neo4j    || true

  [[ "${DO_RETENTION}" == "true" ]] && apply_retention || true

  print_summary
}

main "$@"
