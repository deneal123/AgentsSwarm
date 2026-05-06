
# Orchestrator — агентная оркестрация для роя роботов

Микросервис на базе **OpenAI Agents SDK**, выступающий интеллектуальной прослойкой между пользователем и инфраструктурой управления роботами. Принимает запросы на естественном языке, строит план, маршрутизирует шаги к специализированным агентам, вызывает инструменты через MCP-серверы и транслирует результат в реальном времени через WebSocket.

---

## Быстрый старт

```bash
uv sync
uv run uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000
```

### Docker (dev)

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

Поднимает 5 сервисов:

| Сервис | Порт | Описание |
| --- | --- | --- |
| `orchestrator` | 8000 | FastAPI + Agents SDK |
| `mission-control-mcp` | 8010 | MCP-сервер Mission Control API (SSE) |
| `mission-dispatch-mcp` | 8011 | MCP-сервер Mission Dispatch API (SSE) |
| `ros-msp` | 8012 | MCP-сервер ROS2 через rosbridge WebSocket (FastMCP SSE) |
| `redis` | 6379 | Хранилище сессий |

Код оркестратора монтируется в контейнер через volume с hot-reload.

---

## Конфигурация

Переменные окружения задаются в `src/orchestrator/config/.env` (см. `.env.example`):

```
# Транспорт MCP-серверов (sse = контейнеры, stdio = локальный subprocess)
MISSION_CONTROL_TRANSPORT=sse
MISSION_CONTROL_MCP_URL=http://mission-control-mcp:8000/sse

MISSION_DISPATCH_TRANSPORT=sse
MISSION_DISPATCH_MCP_URL=http://mission-dispatch-mcp:8000/sse

ROS_MSP_TRANSPORT=sse
ROS_MSP_MCP_URL=http://ros-msp:8000/sse

# rosbridge (машина с ROS2 workspace)
ROSBRIDGE_IP=195.225.110.91
ROSBRIDGE_PORT=9090

# Внешние API
MISSION_CONTROL_URL=http://195.225.110.91:8050   # прямой доступ для MapAnalyst
MISSION_DISPATCH_URL=http://185.55.57.82:8051

# Модель
AGENTS_PROVIDER=vllm           # openai | vllm
AGENTS_MODEL=Qwen/Qwen2.5-7B-Instruct
AGENTS_TEMPERATURE=1.0

# Поведение планировщика
PLAN_REPLAN_MAX=1              # макс. повторных планирований при сбое
```

---

## HTTP API

| Метод | Путь | Описание |
| --- | --- | --- |
| `POST` | `/task` | Принять задачу; `?run=false` — только создать без запуска |
| `GET` | `/task/{id}/status` | Текущий статус задачи |
| `GET` | `/task/{id}/plan` | Список шагов плана с их статусами |
| `GET` | `/task/{id}/logs` | Исторический лог |
| `GET` | `/task/{id}/events?after_seq=N` | Потоковые события начиная с порядкового номера N |
| `POST` | `/task/{id}/events` | Внешний push события (воркеры, MCP-серверы) |
| `POST` | `/task/{id}/run` | Запустить отложенную или pending задачу |
| `POST` | `/task/{id}/cancel` | Отменить задачу (чистая остановка всех шагов) |
| `POST` | `/task/{id}/replan` | Пересобрать план; `?run=true` — сразу запустить |
| `WS` | `/ws/task/{id}` | WebSocket-стрим событий задачи |

Interface-сервис (backend + frontend) обращается напрямую к этим эндпоинтам и WebSocket без промежуточного gateway.

---

## Архитектура

```mermaid
graph TB
    User["Пользователь"]
    Interface["Interface Service\n(backend + frontend)"]

    OrchestratorAPI["Orchestrator API\nPOST /task"]
    StreamCollector["StreamCollector\nбуфер событий"]
    WebSocket["WS /ws/task/{id}\n(текст + изображения)"]

    Planner["Planner\nLLM + эвристика"]
    PlanRunner["PlanRunner\nпошаговый исполнитель"]
    Router["Router Agent\nклассификация + handoff"]

    MapAnalyst["MapAnalyst Agent\nанализ карты + маршруты"]
    RobotInfo["RobotInfo Agent"]
    Navigation["Navigation Agent"]
    Swarm["SwarmCoordinator Agent"]
    General["General Agent"]

    MissionControlAPI["Mission Control API\n:8050"]
    RosMSP["ros-msp\nFastMCP SSE\n:8012"]
    MissionControl["mission-control-mcp\nSSE :8010"]
    MissionDispatch["mission-dispatch-mcp\nSSE :8011"]

    IsaacSim["Isaac Sim / VDA5050\n(роботы)"]
    Rosbridge["rosbridge_server\n195.225.110.91:9090"]

    User -->|"HTTP POST /task\nprompt"| Interface
    Interface -->|"POST /task"| OrchestratorAPI
    Interface -->|"WS /ws/task/{id}"| WebSocket

    OrchestratorAPI --> Planner
    Planner -->|"список PlanStep"| PlanRunner
    PlanRunner -->|"шаг за шагом"| Router
    PlanRunner -->|"шаг 3 (если навигация)"| MapAnalyst

    Router -->|"robot_info"| RobotInfo
    Router -->|"navigation"| Navigation
    Router -->|"swarm_coord"| Swarm
    Router -->|"general"| General

    MapAnalyst -->|"GET /api/v1/map"| MissionControlAPI
    MapAnalyst -->|"POST /api/v1/visualize_route"| MissionControlAPI
    RobotInfo -->|"MCP"| RosMSP
    Navigation -->|"MCP"| MissionControl
    Navigation -->|"MCP"| MissionDispatch
    Swarm -->|"MCP"| RosMSP
    Swarm -->|"MCP"| MissionControl
    Swarm -->|"MCP"| MissionDispatch

    RosMSP -->|"WebSocket ws://"| Rosbridge
    Rosbridge -->|"ROS2 topics"| IsaacSim
    MissionControl -->|"HTTP"| MissionControlAPI
    MissionControlAPI -->|"missions"| IsaacSim
    MissionDispatch -->|"HTTP"| IsaacSim

    PlanRunner -->|"события"| StreamCollector
    MapAnalyst -->|"route_images (base64 PNG)"| StreamCollector
    Router -->|"события"| StreamCollector
    StreamCollector --> WebSocket
    WebSocket -->|"push"| Interface

    style User fill:none,stroke:#ff6b6b,stroke-width:2px,color:#fff
    style Interface fill:none,stroke:#ff6b6b,stroke-width:2px,color:#fff
    style OrchestratorAPI fill:none,stroke:#ffa500,stroke-width:2px,color:#fff
    style StreamCollector fill:none,stroke:#ffa500,stroke-width:2px,color:#fff
    style WebSocket fill:none,stroke:#ffa500,stroke-width:2px,color:#fff
    style Planner fill:none,stroke:#ffa500,stroke-width:2px,color:#fff
    style PlanRunner fill:none,stroke:#ffa500,stroke-width:2px,color:#fff
    style Router fill:none,stroke:#52c41a,stroke-width:2px,color:#fff
    style MapAnalyst fill:none,stroke:#1890ff,stroke-width:2px,color:#fff
    style RobotInfo fill:none,stroke:#52c41a,stroke-width:2px,color:#fff
    style Navigation fill:none,stroke:#52c41a,stroke-width:2px,color:#fff
    style Swarm fill:none,stroke:#52c41a,stroke-width:2px,color:#fff
    style General fill:none,stroke:#52c41a,stroke-width:2px,color:#fff
    style RosMSP fill:none,stroke:#9b59b6,stroke-width:2px,color:#fff
    style MissionControl fill:none,stroke:#9b59b6,stroke-width:2px,color:#fff
    style MissionDispatch fill:none,stroke:#9b59b6,stroke-width:2px,color:#fff
    style MissionControlAPI fill:none,stroke:#e67e22,stroke-width:2px,color:#fff
    style IsaacSim fill:none,stroke:#e67e22,stroke-width:2px,color:#fff
    style Rosbridge fill:none,stroke:#e67e22,stroke-width:2px,color:#fff
```

---

## Поток выполнения задачи

1. **Interface** отправляет `POST /task` с промптом → получает `task_id`, открывает `WS /ws/task/{id}`.
2. **Orchestrator** создаёт запись задачи в `TaskStore`, публикует событие `"Task accepted"`.
3. **Planner** (LLM + эвристический fallback) декомпозирует промпт на шаги.
4. **PlanRunner** исполняет шаги последовательно:
   - Перед каждым шагом проверяет статус задачи (если `canceled` или `failed` — прекращает).
   - Шаги навигации/роя автоматически получают результат MapAnalyst в контексте.
   - Специализированный агент вызывает инструменты через MCP.
5. Все события (старт шага, вызов инструмента, результат, ошибка, изображения маршрутов) пишутся в **StreamCollector** и сразу транслируются через WebSocket.
6. После завершения всех шагов задача переходит в `completed`.

### Пример плана для навигационной задачи

```
Шаг 1 — Router          : анализ запроса
Шаг 2 — RobotInfo       : сбор контекста (статус, батарея, позиция)
Шаг 3 — MapAnalyst      : анализ карты, построение маршрутов, выбор лучшего
Шаг 4 — Navigation      : выполнение миссии с учётом контекста карты
```

---

## MapAnalyst — анализ карты и планирование маршрутов

Специализированный агент, вставляемый в план автоматически при любой навигационной или роевой задаче.

### Трёхфазный воркфлоу

**Фаза 1 — Предложение кандидатов**
- Скачивает актуальное изображение карты (`GET /api/v1/map`) и метаданные (`/api/v1/map/metadata`) напрямую из Mission Control.
- Отправляет карту (base64 PNG) + задание в vision-модель.
- Получает ровно 3 кандидата маршрута с разной стратегией:
  - `direct` — минимум точек, прямо к цели
  - `safe` — обходит препятствия с запасом ≥ safety\_distance + 0.3 м
  - `optimal` — баланс длины пути и безопасности

**Фаза 2 — Визуализация маршрутов**
- Для каждого кандидата отправляет waypoints в Mission Control (`POST /api/v1/visualize_route`).
- Получает PNG-изображения с нарисованными маршрутами на реальной карте.
- **Все PNG передаются в WebSocket-стрим** в событии `route_visualizations` — фронтенд может отобразить их пользователю.

**Фаза 3 — Выбор лучшего маршрута (vision LLM)**
- Отправляет все PNG на сравнение vision-модели.
- Критерии: эффективность пути, запас от стен, плавность, риск узких мест.
- Победитель + обоснование передаются в контекст следующего шага (Navigation/SwarmCoordinator).

**Нефатальная архитектура**: любой сбой (карта недоступна, waypoints не на navigable поверхности, vision API недоступен) → возвращает `HandoffResult(success=True, message="")`, план продолжается без контекста карты.

### Формат события `route_visualizations` в WebSocket

```json
{
  "source": "agent-sdk",
  "meta": {
    "type": "route_images",
    "winner": "optimal",
    "images": [
      {
        "name": "direct",
        "image_b64": "<base64 PNG>",
        "mime": "image/png",
        "is_best": false
      },
      {
        "name": "safe",
        "image_b64": "<base64 PNG>",
        "mime": "image/png",
        "is_best": false
      },
      {
        "name": "optimal",
        "image_b64": "<base64 PNG>",
        "mime": "image/png",
        "is_best": true
      }
    ]
  }
}
```

Обнаружение на стороне клиента: `event.meta?.type === "route_images"`.

---

## Fallback-ы и устойчивость

| Уровень | Поведение |
| --- | --- |
| **Шаг плана** | До `max_attempts=2` попыток на шаг. При неустранимой ошибке шаг помечается `failed`. |
| **Весь план** | При провале плана строится новый план и запускается повторно (до `PLAN_REPLAN_MAX=1`). |
| **MapAnalyst** | Любой сбой (карта, API, vision) → нефатальный, план продолжается без контекста карты. |
| **Превышение лимита** | Задача переходит в `failed`, все незавершённые шаги — в `canceled`. |
| **Отмена** | `POST /task/{id}/cancel` — немедленная остановка, шаги помечаются `canceled`. |
| **Ручной перезапуск** | `POST /task/{id}/replan?run=true` — пересобрать план и запустить заново. |
| **Внешние события** | `POST /task/{id}/events` — внешние агенты или воркеры могут напрямую пушить статус. |

> **Ограничение:** оркестратор **не поллирует** выполнение миссии роботом автоматически. После отправки миссии агент считает шаг завершённым по ответу API. Для отслеживания фактического выполнения промпт агента явно инструктирует вызов `get_mission_status()` в цикле.

---

## Поддерживаемые сценарии

| Сценарий | Агент(ы) | MCP-инструменты |
| --- | --- | --- |
| Статус роботов (батарея, позиция) | RobotInfo | `get_robot_status`, `get_topics` |
| Навигация одного робота в точку | MapAnalyst → Navigation | `visualize_route`, `submit_navigation_mission`, `dispatch_mission` |
| Отстыковка робота от дока | Navigation | `submit_undock_mission` |
| Координация нескольких роботов | MapAnalyst → SwarmCoordinator | `visualize_route`, `dispatch_mission`, `submit_navigation_mission` |
| Опрос очереди и статуса миссий | Navigation / RobotInfo | `get_mission_status`, `get_fleet_summary` |
| ROS2-топики и ноды | RobotInfo / Swarm | `get_topics`, `get_nodes`, `subscribe_topic` |
| Общий вопрос без инструментов | General | — |

---

## Планировщик

`Planner` строит план в два этапа:

1. **LLM-планирование** — запрос к языковой модели (OpenAI/vLLM) с промптом, описывающим доступных агентов. Возвращает список `_GoalItem(description, agent, target_robots)`.
2. **Эвристический fallback** — если LLM недоступна или возвращает пустой результат, применяется детерминированная эвристика по ключевым словам и robot\_id в промпте.

### Структура плана

**Для навигационных задач (Navigation или SwarmCoordinator):**

```
Шаг 1 — Router          (depends_on: [])
Шаг 2 — RobotInfo       (depends_on: [1])
Шаг 3 — MapAnalyst      (depends_on: [1], meta.task_description = описание целей)
Шаг 4+ — Navigation/Swarm (depends_on: [1, 2, 3])
```

**Для информационных задач (RobotInfo, General):**

```
Шаг 1 — Router          (depends_on: [])
Шаг 2 — RobotInfo       (depends_on: [1])
Шаг 3 — RobotInfo/General (depends_on: [1, 2])
```

### Контекстная инъекция MapAnalyst → Navigation

После выполнения MapAnalyst PlanRunner автоматически инжектирует результат анализа карты в описание и мета всех последующих шагов Navigation и SwarmCoordinator:

```python
step.meta["map_context"] = map_analyst_result
step.description += f"\n\nКонтекст карты:\n{map_analyst_result}"
```

Navigation агент использует координаты из контекста карты и текущую позицию робота из `get_robot_status` для формирования итоговых waypoints.

---

## MCP-серверы

### mission-control-mcp
Обёртка над HTTP API Mission Control (`http://195.225.110.91:8050`).

| Инструмент | Описание |
| --- | --- |
| `submit_navigation_mission` | Навигация по маршрутным точкам (waypoints) |
| `submit_undock_mission` | Отстыковка от дока |
| `visualize_route` | Получить PNG-визуализацию маршрута |
| `get_map_info` | Метаданные текущей карты |
| `list_available_maps` | Список загруженных карт |
| `select_map` | Активировать карту |
| `deploy_map_to_robot` | Загрузить карту на робота |
| `get_detected_objects` | Объекты из камеры робота |
| `submit_objective` | Behavior tree objective |
| `submit_pick_and_place` | Миссия манипулятора |

### mission-dispatch-mcp
Обёртка над HTTP API Mission Dispatch (`http://185.55.57.82:8051`).

| Инструмент | Описание |
| --- | --- |
| `get_robot_status` | Статус, батарея, позиция, состояние |
| `get_fleet_summary` | Сводка по всему флоту |
| `get_idle_robots` | Роботы в состоянии IDLE |
| `get_mission_status` | Статус миссий с фильтрами |
| `dispatch_mission` | Отправить робота в координату |
| `get_recent_failures` | Последние сбои миссий |

### ros-msp
FastMCP-сервер, подключающийся к **rosbridge WebSocket** (`ws://195.225.110.91:9090`).
Не требует ROS2 на машине с оркестратором — только сетевой доступ к rosbridge.

| Инструмент | Описание |
| --- | --- |
| `get_topics` | Список ROS2-топиков |
| `subscribe_once` | Прочитать одно сообщение из топика |
| `get_nodes` | Список ROS2-нод |
| `get_parameter` | Параметры ноды |
| `connect_to_robot` | Подключиться к другому rosbridge |

**Требование:** на машине `195.225.110.91` в контейнере `vda5050_client` должен быть запущен `rosbridge_server`:
```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### Транспорт MCP

| Режим | Когда | Конфигурация |
| --- | --- | --- |
| `sse` (Docker) | Все три MCP работают как контейнеры | `*_TRANSPORT=sse`, `*_MCP_URL=http://<service>:8000/sse` |
| `stdio` (local) | Локальная разработка без Docker | `*_TRANSPORT=stdio`, `*_COMMAND`, `*_ARGS` |

---

## WebSocket — формат событий

Все события имеют единую структуру:

```json
{
  "task_id": "abc123",
  "source": "agent-sdk",
  "message": "Route visualizations ready (2 images)",
  "level": "info",
  "ts": "2026-05-06T09:43:38.000000+00:00",
  "meta": { "event_type": "route_visualizations", "..." : "..." }
}
```

| `source` | Смысл |
| --- | --- |
| `api` | HTTP API (task accepted) |
| `planner` | Создание/старт шагов плана |
| `agent` | PlanRunner: handoff, step completed |
| `agent-sdk` | Agents SDK: tool calls, agent output, route images |
| `orchestrator` | Оркестратор: replan, внутренние события |

**Специальные события** (определяются по `meta.type`):

| `meta.type` | Смысл | Полезная нагрузка |
| --- | --- | --- |
| `route_images` | PNG маршрутов от MapAnalyst | `meta.images[]` — массив `{name, image_b64, mime, is_best}` |

Инкрементальный polling: `GET /task/{id}/events?after_seq=N` — возвращает только события с seq > N, плюс `last_seq` для следующего запроса.

---

## Управление сессиями

Redis (или in-memory при отсутствии) хранит контекст сессии для поддержки диалога:
- последний использованный `robot_id`
- история запросов
- произвольные данные из `session_data` запроса

`POST /task` принимает опциональное поле `session_data` для передачи начального контекста.

---

## Структура проекта

```
orchestrator/
├── docker/
│   ├── docker-compose.dev.yml
│   ├── Dockerfile                       # образ оркестратора
│   ├── mission-control-mcp/             # MCP Mission Control (mcp + SSE)
│   │   └── src/
│   │       ├── server.py                # 14 инструментов, SSE/stdio транспорт
│   │       └── queries.py               # MissionControlClient (HTTP)
│   ├── mission-dispatch-mcp/            # MCP Mission Dispatch (mcp + SSE)
│   │   └── src/
│   │       ├── server.py
│   │       └── queries.py               # MissionDispatchClient (HTTP)
│   └── ros-msp/                         # MCP ROS2 (fastmcp + rosbridge)
│       └── main.py                      # rosbridge WebSocket tools
└── src/orchestrator/
    ├── agents/
    │   ├── mcp.py                       # конфигурация MCP-серверов
    │   ├── prompts.py                   # системные промпты 5 агентов
    │   └── router.py                    # handoff-конфигурация роутера
    ├── api/
    │   ├── routes/task_routes.py        # HTTP + WebSocket эндпоинты
    │   └── schemas.py
    ├── config/
    │   ├── settings.toml
    │   ├── .env                         # рабочая конфигурация
    │   └── .env.example
    └── services/
        ├── agents_sdk.py                # AgentsSDKExecutor + MapAnalyst pipeline
        ├── map_analyst.py               # get_map_context() — прямой fetch карты
        ├── orchestrator_runtime.py      # build_plan + run_task
        ├── plan_runner.py               # пошаговый исполнитель + map context injection
        ├── planner.py                   # LLM + эвристический builder плана
        ├── streaming.py                 # StreamCollector
        ├── task_application_service.py
        ├── task_event_ingestion_service.py
        └── tasks.py                     # TaskStore + TaskInfo
```

### Агенты

| Агент | Назначение | MCP-серверы |
| --- | --- | --- |
| **Router** | Классификация запроса, handoff к нужному агенту | — |
| **RobotInfo** | Статус роботов, ROS2-диагностика | ros-msp, mission-dispatch-mcp |
| **MapAnalyst** | Анализ карты, генерация маршрутов, сравнение через vision LLM | Прямой HTTP к Mission Control |
| **Navigation** | Навигация одного робота, мониторинг миссии | mission-control-mcp, mission-dispatch-mcp |
| **SwarmCoordinator** | Координация нескольких роботов параллельно | все три MCP |
| **General** | Ответы на вопросы без инструментов | — |
