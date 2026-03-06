# TODO: Интеграционное тестирование и MVP

Кросс-сервисная интеграция, E2E-тесты, финальная сборка MVP.

---

## Этап 1 — Контракты и интерфейсы

- [ ] **Protobuf contract tests.** Проверка совместимости: Orchestrator gRPC client ↔ Triton/vLLM/SmolVLA gRPC servers. Автоматическая генерация mock-серверов из proto-файлов.

- [ ] **OpenAPI contract tests.** Gateway REST API schema → автоматическая генерация TypeScript-типов для Frontend. Проверка: response types совпадают с frontend types.

- [ ] **MQTT topic contract.** Валидация: все MQTT-топики, используемые RobotEdge, совпадают с подписками Communication Bridge и Orchestrator. JSON schema для каждого топика.

- [ ] **RabbitMQ message contract.** Валидация: routing keys и message formats, используемые Gateway ↔ Orchestrator ↔ Communication Service, согласованы. Schema registry.

---

## Этап 2 — Интеграционные тесты (пары сервисов)

- [ ] **Gateway → Orchestrator.** Тест: POST /chat/message → RabbitMQ `commands.user` → Orchestrator consume → task created in PostgreSQL → event published → Gateway WS → client notification.

- [ ] **Orchestrator → MQTT → Robot.** Тест: Orchestrator publish command → MQTT `commands/{robot_id}/move` → mock robot subscribe → ack → MQTT `ack/{robot_id}` → Orchestrator receives ack.

- [ ] **Robot → Communication Bridge → Orchestrator.** Тест: mock robot publish telemetry → MQTT → Bridge → RabbitMQ → Orchestrator consume → Redis Feature Store updated.

- [ ] **Orchestrator → vLLM.** Тест: Orchestrator sends chat completion request → vLLM processes → structured JSON response → Orchestrator parses plan.

- [ ] **Orchestrator → Triton.** Тест: Orchestrator sends detection request (image bytes) → Triton processes → list[Detection] response → Orchestrator updates Feature Store.

- [ ] **Orchestrator → SmolVLA.** Тест: Orchestrator sends PredictAction RPC (image + instruction) → SmolVLA processes → ActionChunk response → Orchestrator publishes to MQTT.

- [ ] **Gateway → Redis → Gateway (WebSocket fan-out).** Тест: Gateway pod1 receives event → Redis Pub/Sub → Gateway pod2 forwards to connected WebSocket client.

---

## Этап 3 — E2E сценарии

- [ ] **Сценарий: простая команда.** Оператор отправляет "Робот 1, подойди к зоне А" через chat → Gateway → Orchestrator (LangGraph: intake → plan → assign → execute) → MQTT command → mock robot executes → ack → task completed → notification в UI.

- [ ] **Сценарий: мультироботная задача.** "Все роботы, проведите инспекцию зоны B" → Orchestrator декомпозирует на подзадачи (Send API) → назначает 3 роботов → параллельное выполнение → агрегация результатов → отчёт пользователю.

- [ ] **Сценарий: детекция объекта.** "Робот 2, найди красную коробку" → Orchestrator → запрос камеры робота → Triton detection → SmolVLA plan grasp → robot executes → result photo → confirmation.

- [ ] **Сценарий: потеря связи.** Робот теряет MQTT-соединение → LWT публикуется → Orchestrator получает offline event → Dashboard обновляет статус → робот работает автономно → восстановление связи → sync.

- [ ] **Сценарий: перепланирование.** Задача assigned → робот сообщает failure (obstacle) → Orchestrator evaluation → replan (другой маршрут или другой робот) → retry → success.

- [ ] **Сценарий: emergency stop.** Оператор нажимает E-Stop в UI → Gateway → Orchestrator → MQTT QoS 2 → robot stops → incident created → audit log.

---

## Этап 4 — Нагрузочное тестирование

- [ ] **Телеметрия.** Нагрузка: 100 виртуальных роботов, каждый отправляет 10 msg/sec телеметрии через MQTT. Проверка: bridge throughput, InfluxDB write rate, Redis update rate, Dashboard render performance.

- [ ] **API Gateway.** Нагрузка: 1000 req/sec на REST endpoints (GET /robots, GET /tasks). Проверка: p99 latency < 200ms, error rate < 0.1%.

- [ ] **WebSocket.** Нагрузка: 500 одновременных WebSocket-соединений, каждое получает 5 updates/sec. Проверка: memory usage Gateway, message delivery latency.

- [ ] **AI Inference.** Нагрузка: 50 concurrent detection requests. Проверка: Triton dynamic batching, p99 latency < 100ms, GPU utilization > 80%.

- [ ] **LangGraph.** Нагрузка: 20 concurrent planning workflows. Проверка: PostgresSaver checkpoint write time, Redis state update, task completion time.

---

## Этап 5 — Симулятор роботов

- [ ] **Robot simulator.** Python-скрипт, имитирующий N роботов: MQTT подключение, периодическая публикация телеметрии (случайная позиция в пределах зоны + battery drain), приём и ack команд, имитация movement (линейная интерполяция к target).

- [ ] **Configurable scenarios.** YAML-конфигурация: количество роботов, начальные позиции, типы роботов, сценарии (normal operation, random failures, battery drain, network flapping).

- [ ] **Gazebo integration (опционально).** ROS 2 Gazebo simulation: реалистичная физика, камеры (synthetic images), LiDAR, navigation stack. Для полноценного E2E тестирования SmolVLA и navigation.

---

## Этап 6 — MVP Checklist

- [ ] **Инфраструктура.** Docker Compose запускает все сервисы (make up). Health check проходит для всех (make health). Seed data загружены (make seed).

- [ ] **Auth flow.** Login → JWT → protected endpoints. Роли: operator (view + chat), admin (full access).

- [ ] **Dashboard.** Отображает роботы (real-time status), задачи (kanban), метрики (cards). Данные обновляются через WebSocket.

- [ ] **Chat.** Отправка команды → streaming ответ от LLM → задача создаётся → отслеживание в Dashboard.

- [ ] **Robot command.** Команда через chat → LangGraph plan → MQTT publish → robot (simulator) ack → task completed → notification.

- [ ] **Telemetry.** Robot → MQTT → Bridge → InfluxDB. Dashboard показывает historical telemetry графики.

- [ ] **3D Visualization.** Карта зон, роботы на карте (real-time position), базовая навигация камеры.

- [ ] **AI Detection.** Изображение → Triton → detections → Feature Store → Dashboard отображает.

- [ ] **Monitoring.** Prometheus scrapes all services. Grafana dashboards (Swarm Overview, Robot Telemetry). Jaeger traces для debugging.

- [ ] **CI/CD.** Lint + tests проходят на PR. Docker images собираются и пушатся. Integration tests проходят.

---

## Этап 7 — Документация MVP

- [ ] **README.md (root).** Quick start: prerequisites, clone, make up, open browser. Architecture diagram (mermaid). Links на документацию.

- [ ] **API documentation.** OpenAPI spec авто-генерируется из FastAPI. Hosted на /docs (Swagger UI). Примеры запросов для каждого endpoint.

- [ ] **Architecture Decision Records.** ADR для ключевых решений: почему LangGraph, почему MQTT + RabbitMQ (а не только один), почему SmolVLA, почему Redis Feature Store.

- [ ] **Deployment guide.** Пошаговая инструкция: dev setup (Docker Compose), staging (Kubernetes + Helm), production (HA, backup, monitoring).

- [ ] **Contributing guide.** Стиль кода, branching strategy, PR template, commit conventions, testing requirements.
