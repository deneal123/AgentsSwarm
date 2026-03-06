-- ===========================================================================
-- Neo4j Init Cypher Script for AgentsSwarm
-- Loaded via docker-entrypoint-initdb.d (NEO4J_PLUGINS: apoc)
-- ===========================================================================

// ── Constraints (unique) ────────────────────────────────────────────────────
CREATE CONSTRAINT robot_id_unique IF NOT EXISTS
  FOR (r:Robot) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT zone_id_unique IF NOT EXISTS
  FOR (z:Zone) REQUIRE z.id IS UNIQUE;

CREATE CONSTRAINT task_id_unique IF NOT EXISTS
  FOR (t:Task) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT object_id_unique IF NOT EXISTS
  FOR (o:Object) REQUIRE o.id IS UNIQUE;

// ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX robot_status_idx IF NOT EXISTS
  FOR (r:Robot) ON (r.status);

CREATE INDEX robot_zone_idx IF NOT EXISTS
  FOR (r:Robot) ON (r.zone_id);

CREATE INDEX task_status_idx IF NOT EXISTS
  FOR (t:Task) ON (t.status);

CREATE INDEX zone_name_idx IF NOT EXISTS
  FOR (z:Zone) ON (z.name);

CREATE INDEX object_type_idx IF NOT EXISTS
  FOR (o:Object) ON (o.type);

// ── Initial Zones ────────────────────────────────────────────────────────────
MERGE (z1:Zone {id: 'zone_warehouse_A', name: 'Склад А', type: 'warehouse'})
  ON CREATE SET z1.created_at = datetime(), z1.capacity = 50;

MERGE (z2:Zone {id: 'zone_warehouse_B', name: 'Склад Б', type: 'warehouse'})
  ON CREATE SET z2.created_at = datetime(), z2.capacity = 50;

MERGE (z3:Zone {id: 'zone_charging', name: 'Станция зарядки', type: 'charging'})
  ON CREATE SET z3.created_at = datetime(), z3.capacity = 10;

MERGE (z4:Zone {id: 'zone_corridor', name: 'Коридор', type: 'corridor'})
  ON CREATE SET z4.created_at = datetime(), z4.capacity = 0;

// ── Zone Adjacency Relationships ─────────────────────────────────────────────
MATCH (a:Zone {id: 'zone_warehouse_A'}), (c:Zone {id: 'zone_corridor'})
  MERGE (a)-[:ADJACENT_TO {distance_m: 15.0}]->(c);

MATCH (b:Zone {id: 'zone_warehouse_B'}), (c:Zone {id: 'zone_corridor'})
  MERGE (b)-[:ADJACENT_TO {distance_m: 20.0}]->(c);

MATCH (c:Zone {id: 'zone_corridor'}), (ch:Zone {id: 'zone_charging'})
  MERGE (c)-[:ADJACENT_TO {distance_m: 8.0}]->(ch);

RETURN 'Neo4j initialization complete' AS message;
