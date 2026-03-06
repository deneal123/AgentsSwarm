#!/usr/bin/env bash
# =============================================================================
# seed-data.sh — загрузка тестовых данных для разработки
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║       AgentsSwarm — Seed Data                    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

if [[ -f "${SCRIPT_DIR}/../../.env" ]]; then
    set -a; source "${SCRIPT_DIR}/../../.env"; set +a
fi

PG="docker compose -f ${SCRIPT_DIR}/../../docker-compose.dev.yml exec -T postgres psql -U ${POSTGRES_USER:-agentsswarm} -d ${POSTGRES_DB:-agentsswarm}"

# ─── Пользователи ─────────────────────────────────────────────────────────────
echo "▶  Создание пользователей..."
$PG <<'SQL'
INSERT INTO users (id, name, email, role, password_hash, is_active)
VALUES
    (gen_random_uuid(), 'Admin User',    'admin@agentsswarm.local',    'ADMIN',    crypt('admin123',    gen_salt('bf')), true),
    (gen_random_uuid(), 'Operator User', 'operator@agentsswarm.local', 'OPERATOR', crypt('operator123', gen_salt('bf')), true),
    (gen_random_uuid(), 'Viewer User',   'viewer@agentsswarm.local',   'OPERATOR', crypt('viewer123',   gen_salt('bf')), true)
ON CONFLICT DO NOTHING;
SQL
echo "   ✓  Пользователи созданы"

# ─── Зоны ─────────────────────────────────────────────────────────────────────
echo "▶  Создание зон..."
$PG <<'SQL'
INSERT INTO zones (id, name, type, max_robots, boundaries)
VALUES
    ('zone-warehouse-a', 'Warehouse Zone A', 'WAREHOUSE',    10, '{"x_min":0,"y_min":0,"x_max":50,"y_max":50}'),
    ('zone-warehouse-b', 'Warehouse Zone B', 'WAREHOUSE',    10, '{"x_min":50,"y_min":0,"x_max":100,"y_max":50}'),
    ('zone-inspection',  'Inspection Area',  'INSPECTION',    5, '{"x_min":0,"y_min":50,"x_max":100,"y_max":100}'),
    ('zone-charging',    'Charging Station', 'CHARGING',     20, '{"x_min":45,"y_min":45,"x_max":55,"y_max":55}')
ON CONFLICT DO NOTHING;
SQL
echo "   ✓  Зоны созданы"

# ─── Роботы ───────────────────────────────────────────────────────────────────
echo "▶  Создание роботов..."
$PG <<'SQL'
INSERT INTO robots (id, model, serial_number, status, battery_level, zone_id, config)
VALUES
    ('robot-001', 'MobileManipulator-X1', 'SN-001', 'IDLE',   92, 'zone-warehouse-a', '{"capabilities":["navigation","manipulation","camera"]}'),
    ('robot-002', 'MobileManipulator-X1', 'SN-002', 'IDLE',   78, 'zone-warehouse-a', '{"capabilities":["navigation","manipulation","camera"]}'),
    ('robot-003', 'InspectionDrone-D2',   'SN-003', 'IDLE',   85, 'zone-inspection',  '{"capabilities":["navigation","camera","lidar"]}'),
    ('robot-004', 'GroundScout-S1',       'SN-004', 'CHARGING', 15,'zone-charging',   '{"capabilities":["navigation","camera"]}'),
    ('robot-005', 'MobileManipulator-X1', 'SN-005', 'IDLE',   55, 'zone-warehouse-b', '{"capabilities":["navigation","manipulation","camera"]}')
ON CONFLICT DO NOTHING;
SQL
echo "   ✓  Роботы созданы (5 шт.)"

# ─── Задачи ───────────────────────────────────────────────────────────────────
echo "▶  Создание тестовых задач..."
$PG <<'SQL'
INSERT INTO tasks (id, type, status, priority, params, result)
VALUES
    (gen_random_uuid(), 'NAVIGATE', 'COMPLETED', 5, '{"target_zone":"zone-warehouse-a","robot_id":"robot-001"}', '{"success":true,"duration_s":45}'),
    (gen_random_uuid(), 'INSPECT',  'COMPLETED', 3, '{"zone_id":"zone-inspection","robot_id":"robot-003"}',      '{"success":true,"anomalies":0}'),
    (gen_random_uuid(), 'PICK_UP',  'FAILED',    4, '{"object_class":"red_box","robot_id":"robot-002"}',         '{"success":false,"error":"object_not_found"}'),
    (gen_random_uuid(), 'NAVIGATE', 'PENDING',   2, '{"target_zone":"zone-warehouse-b"}',                        null),
    (gen_random_uuid(), 'SCAN',     'IN_PROGRESS',3,'{"zone_id":"zone-warehouse-a","robot_id":"robot-001"}',     null)
ON CONFLICT DO NOTHING;
SQL
echo "   ✓  Задачи созданы (5 шт.)"

# ─── Redis: начальные состояния роботов ───────────────────────────────────────
echo "▶  Инициализация Redis Feature Store..."
docker compose -f "${SCRIPT_DIR}/../../docker-compose.dev.yml" exec -T redis \
    redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-changeme}" <<'REDIS'
HSET robot:robot-001:state status IDLE battery 92 position_x 10 position_y 20 zone_id zone-warehouse-a last_seen 0
HSET robot:robot-002:state status IDLE battery 78 position_x 15 position_y 25 zone_id zone-warehouse-a last_seen 0
HSET robot:robot-003:state status IDLE battery 85 position_x 60 position_y 70 zone_id zone-inspection  last_seen 0
HSET robot:robot-004:state status CHARGING battery 15 position_x 50 position_y 50 zone_id zone-charging last_seen 0
HSET robot:robot-005:state status IDLE battery 55 position_x 80 position_y 10 zone_id zone-warehouse-b last_seen 0
REDIS
echo "   ✓  Redis Feature Store инициализирован"

# ─── InfluxDB: генерация тестовой телеметрии ──────────────────────────────────
echo "▶  Генерация телеметрии в InfluxDB (последний час)..."
python3 - <<'PYEOF'
import time
import random
import urllib.request
import urllib.parse
import os

INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN = os.getenv("INFLUXDB_ADMIN_TOKEN", "changeme-influx-admin-token")
ORG = os.getenv("INFLUXDB_ORG", "agentsswarm")
BUCKET = os.getenv("INFLUXDB_BUCKET_TELEMETRY", "telemetry")

robots = [
    ("robot-001", "MobileManipulator-X1", "zone-warehouse-a"),
    ("robot-002", "MobileManipulator-X1", "zone-warehouse-a"),
    ("robot-003", "InspectionDrone-D2",   "zone-inspection"),
    ("robot-005", "GroundScout-S1",       "zone-warehouse-b"),
]

now_ns = int(time.time() * 1e9)
lines = []

for robot_id, model, zone_id in robots:
    battery = random.randint(50, 95)
    for i in range(60):   # 60 точек, 1 в минуту
        ts = now_ns - (60 - i) * 60 * int(1e9)
        batt = max(0, battery - i * 0.3 + random.gauss(0, 0.5))
        vx = random.gauss(0, 0.5)
        vy = random.gauss(0, 0.5)
        lines.append(
            f"robot_telemetry,robot_id={robot_id},robot_model={model},zone_id={zone_id} "
            f"battery={batt:.1f},velocity={abs(vx+vy):.2f},"
            f"position_x={random.gauss(10,3):.2f},position_y={random.gauss(20,3):.2f} "
            f"{ts}"
        )

payload = "\n".join(lines).encode()
url = f"{INFLUX_URL}/api/v2/write?org={urllib.parse.quote(ORG)}&bucket={urllib.parse.quote(BUCKET)}&precision=ns"
req = urllib.request.Request(url, data=payload, method="POST",
                              headers={"Authorization": f"Token {TOKEN}", "Content-Type": "text/plain"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"   ✓  InfluxDB: {len(lines)} точек телеметрии записано (HTTP {r.status})")
except Exception as e:
    print(f"   ⚠️  InfluxDB недоступен: {e}")
PYEOF

# ─── Neo4j: граф роботов и зон ────────────────────────────────────────────────
echo "▶  Инициализация Neo4j графа (роботы и зоны)..."
docker compose -f "${SCRIPT_DIR}/../../docker-compose.dev.yml" exec -T neo4j \
    cypher-shell -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD:-neo4j_secret}" \
    --format plain <<'CYPHER'
// Создаём узлы Robot с начальными свойствами
MERGE (r1:Robot {id: 'robot-001'})
  SET r1.model = 'MobileManipulator-X1', r1.serial = 'SN-001', r1.status = 'IDLE', r1.battery = 92.0
MERGE (r2:Robot {id: 'robot-002'})
  SET r2.model = 'MobileManipulator-X1', r2.serial = 'SN-002', r2.status = 'IDLE', r2.battery = 78.0
MERGE (r3:Robot {id: 'robot-003'})
  SET r3.model = 'InspectionDrone-D2',   r3.serial = 'SN-003', r3.status = 'IDLE', r3.battery = 85.0
MERGE (r4:Robot {id: 'robot-004'})
  SET r4.model = 'GroundScout-S1',       r4.serial = 'SN-004', r4.status = 'CHARGING', r4.battery = 15.0
MERGE (r5:Robot {id: 'robot-005'})
  SET r5.model = 'MobileManipulator-X1', r5.serial = 'SN-005', r5.status = 'IDLE', r5.battery = 55.0;

// Связываем роботов с зонами через LOCATED_IN
MATCH (r:Robot {id: 'robot-001'}), (z:Zone {id: 'zone_warehouse_A'})
  MERGE (r)-[:LOCATED_IN {since: datetime()}]->(z);
MATCH (r:Robot {id: 'robot-002'}), (z:Zone {id: 'zone_warehouse_A'})
  MERGE (r)-[:LOCATED_IN {since: datetime()}]->(z);
MATCH (r:Robot {id: 'robot-003'}), (z:Zone {id: 'zone_inspection'})
  MERGE (r)-[:LOCATED_IN {since: datetime()}]->(z);
MATCH (r:Robot {id: 'robot-004'}), (z:Zone {id: 'zone_charging'})
  MERGE (r)-[:LOCATED_IN {since: datetime()}]->(z);
MATCH (r:Robot {id: 'robot-005'}), (z:Zone {id: 'zone_warehouse_B'})
  MERGE (r)-[:LOCATED_IN {since: datetime()}]->(z);

// Создаём тестовый Task-узел (выполненное задание)
MERGE (t1:Task {id: 'task-seed-001'})
  SET t1.type = 'NAVIGATE', t1.status = 'COMPLETED', t1.priority = 5;
MATCH (r:Robot {id: 'robot-001'}), (t:Task {id: 'task-seed-001'})
  MERGE (r)-[:EXECUTED {completed_at: datetime()}]->(t);
CYPHER
echo "   ✓  Neo4j граф инициализирован (5 роботов, связи с зонами)"

# ─── MinIO: загрузка тестовых данных ──────────────────────────────────────────
echo "▶  MinIO: создание placeholder объектов..."
if command -v mc &> /dev/null; then
    mc alias set agentsswarm "${MINIO_URL:-http://localhost:9000}" \
        "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minio_secret}" \
        --api S3v4 > /dev/null 2>&1 || true

    # Загружаем placeholder-файлы для проверки работы бакетов
    echo '{"name":"default-map","version":"1.0","created":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}' | \
        mc pipe agentsswarm/maps/default-map.json > /dev/null 2>&1 \
        && echo "   ✓  MinIO: maps/default-map.json загружен" \
        || echo "   ⚠️  MinIO: не удалось загрузить тестовый файл"
else
    echo "   ⚠️  mc не установлен — MinIO placeholder-файлы пропущены"
fi

echo ""
echo "✅  Seed data загружен."
echo ""
echo "   Пользователи:"
echo "     admin@agentsswarm.local    / admin123"
echo "     operator@agentsswarm.local / operator123"
echo "     viewer@agentsswarm.local   / viewer123"
