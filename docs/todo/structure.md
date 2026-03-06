# Структура проекта AgentsSwarm

## Корневой репозиторий (AgentsSwarm)

Мета-репозиторий, объединяющий все микросервисы через git submodules и содержащий общую инфраструктуру развёртывания.

```
AgentsSwarm/
├── .gitmodules
├── .gitignore
├── README.md
├── LICENSE
├── Makefile
├── build.sh
├── run.sh
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .env
│
├── docs/
│   ├── agent_swarm_general/        # Техническая документация по архитектуре
│   │   ├── Architecture/
│   │   ├── CommunicationService/
│   │   ├── DataStorage/
│   │   ├── Frontend/
│   │   ├── GatewayService/
│   │   ├── Orchestrator/
│   │   ├── RobotEdge/
│   │   ├── SmolVLA/
│   │   ├── TritonInference/
│   │   └── vLLMService/
│   ├── tools/                      # Справочные материалы по библиотекам
│   └── todo/                       # Планы реализации
│
├── infrastructure/
│   │
│   └── scripts/
│       ├── init-db.sh              # Инициализация БД
│       ├── seed-data.sh            # Тестовые данные
│       ├── backup.sh               # Бэкапы
│       └── health-check.sh         # Проверка здоровья всех сервисов
│
├── proto/                          # Общие Protobuf-контракты
│   ├── buf.yaml
│   ├── buf.gen.yaml
│   ├── gateway/
│   │   └── v1/
│   │       └── gateway.proto
│   ├── orchestrator/
│   │   └── v1/
│   │       └── orchestrator.proto
│   ├── inference/
│   │   └── v1/
│   │       ├── triton.proto
│   │       ├── vllm.proto
│   │       └── smolvla.proto
│   └── common/
│       └── v1/
│           ├── types.proto
│           └── telemetry.proto
│
└── services/                       # Git submodules микросервисов
    ├── gateway_service/
    ├── orchestrator/
    ├── vllm_service/
    ├── triton_inference/
    ├── smolvla_service/
    ├── communication_service/
    ├── robot_edge/
    └── frontend/
```

---

## Gateway Service

```
gateway_service/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── README.md
│
├── src/
│   └── gateway/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory, lifespan
│       ├── config.py               # Pydantic Settings (env vars)
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py             # FastAPI dependencies (get_db, get_redis, get_current_user)
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py       # Главный роутер v1
│       │       ├── robots.py       # CRUD роботов
│       │       ├── tasks.py        # CRUD задач
│       │       ├── users.py        # Управление пользователями
│       │       ├── chat.py         # Chat REST endpoints
│       │       ├── telemetry.py    # Телеметрия (запросы к InfluxDB)
│       │       ├── zones.py        # Управление зонами
│       │       └── health.py       # Health/readiness probes
│       │
│       ├── ws/
│       │   ├── __init__.py
│       │   ├── manager.py          # WebSocket connection manager
│       │   ├── handlers.py         # Обработчики WS-сообщений (chat, telemetry, notifications)
│       │   └── router.py           # WebSocket роутер
│       │
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── jwt.py              # Создание/валидация JWT
│       │   ├── middleware.py        # Auth middleware
│       │   ├── permissions.py      # RBAC (role-based access)
│       │   └── schemas.py          # Auth Pydantic schemas
│       │
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── robot.py
│       │   ├── task.py
│       │   ├── user.py
│       │   ├── telemetry.py
│       │   ├── chat.py
│       │   └── common.py           # Pagination, Error, etc.
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── rabbitmq.py         # RabbitMQ publisher client
│       │   ├── redis_client.py     # Redis client (cache, pub/sub)
│       │   ├── grpc_client.py      # gRPC client к Orchestrator
│       │   └── rate_limiter.py     # Rate limiting logic
│       │
│       └── middleware/
│           ├── __init__.py
│           ├── cors.py
│           ├── tracing.py          # OpenTelemetry tracing middleware
│           ├── logging.py          # Structured logging middleware
│           └── error_handler.py    # Global exception handler
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_schemas.py
│   │   └── test_rate_limiter.py
│   └── integration/
│       ├── test_api_robots.py
│       ├── test_api_tasks.py
│       └── test_websocket.py
```

---

## Orchestrator

```
orchestrator/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── Dockerfile.celery               # Отдельный образ для Celery workers
├── README.md
│
├── src/
│   └── orchestrator/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint (FastAPI для health + gRPC server)
│       ├── config.py               # Pydantic Settings
│       │
│       ├── celery_app/
│       │   ├── __init__.py
│       │   ├── app.py              # Celery app instance + config
│       │   ├── tasks/
│       │   │   ├── __init__.py
│       │   │   ├── planning.py     # Задачи планирования
│       │   │   ├── execution.py    # Задачи выполнения команд
│       │   │   ├── monitoring.py   # Задачи мониторинга статуса
│       │   │   └── maintenance.py  # Периодические задачи (cleanup, health)
│       │   └── schedules.py        # Celery Beat расписание
│       │
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── state.py            # SwarmState (TypedDict) + reducers
│       │   ├── main_graph.py       # Главный StateGraph (entry point)
│       │   ├── nodes/
│       │   │   ├── __init__.py
│       │   │   ├── intake.py       # Приём и классификация команды
│       │   │   ├── planning.py     # Генерация плана через LLM
│       │   │   ├── assignment.py   # Назначение роботов (Send API)
│       │   │   ├── execution.py    # Контроль выполнения
│       │   │   ├── evaluation.py   # Оценка результата
│       │   │   └── reporting.py    # Формирование ответа пользователю
│       │   ├── subgraphs/
│       │   │   ├── __init__.py
│       │   │   ├── navigation.py   # Подграф навигационных задач
│       │   │   ├── manipulation.py # Подграф манипуляционных задач
│       │   │   ├── inspection.py   # Подграф инспекционных задач
│       │   │   └── search.py       # Подграф поисковых задач
│       │   └── checkpointing/
│       │       ├── __init__.py
│       │       ├── postgres_saver.py
│       │       └── redis_saver.py
│       │
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── context.py          # SwarmContext (RunContextWrapper)
│       │   ├── planner_agent.py    # Агент-планировщик
│       │   ├── executor_agent.py   # Агент-исполнитель
│       │   ├── monitor_agent.py    # Агент-монитор
│       │   ├── safety_agent.py     # Агент безопасности
│       │   ├── tools/
│       │   │   ├── __init__.py
│       │   │   ├── robot_tools.py  # Инструменты для управления роботами
│       │   │   ├── query_tools.py  # Запросы к БД и Feature Store
│       │   │   ├── vision_tools.py # Вызовы Triton/vLLM
│       │   │   └── mqtt_tools.py   # Отправка MQTT-команд
│       │   ├── guardrails/
│       │   │   ├── __init__.py
│       │   │   ├── input_guards.py
│       │   │   ├── output_guards.py
│       │   │   └── safety_guards.py
│       │   └── handoffs.py         # Правила передачи между агентами
│       │
│       ├── managers/
│       │   ├── __init__.py
│       │   ├── task_manager.py     # Управление жизненным циклом задач
│       │   ├── resource_manager.py # Реестр и назначение роботов
│       │   └── coordination.py     # Координация совместных задач
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── mqtt_client.py      # MQTT publisher/subscriber
│       │   ├── rabbitmq.py         # RabbitMQ consumer/publisher
│       │   ├── redis_client.py     # Redis (cache, Feature Store, pub/sub)
│       │   ├── grpc_server.py      # gRPC server для Gateway
│       │   ├── grpc_clients.py     # gRPC clients (Triton, vLLM, SmolVLA)
│       │   └── postgres.py         # SQLAlchemy engine + session
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py             # SQLAlchemy Base
│       │   ├── robot.py            # Robot ORM model
│       │   ├── task.py             # Task ORM model
│       │   ├── user.py             # User ORM model
│       │   ├── incident.py         # Incident ORM model
│       │   ├── audit.py            # AuditLog ORM model
│       │   ├── zone.py             # Zone ORM model
│       │   └── model_version.py    # ModelVersion ORM model
│       │
│       └── schemas/
│           ├── __init__.py
│           ├── robot.py
│           ├── task.py
│           ├── command.py
│           └── telemetry.py
│
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_state.py
│   │   ├── test_agents.py
│   │   ├── test_guardrails.py
│   │   └── test_managers.py
│   └── integration/
│       ├── test_graph.py
│       ├── test_celery_tasks.py
│       └── test_mqtt.py
│
└── scripts/
    ├── run_worker.sh
    └── run_beat.sh
```

---

## vLLM Service

```
vllm_service/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile                      # На основе nvidia/cuda или vllm/vllm-openai
├── README.md
│
├── src/
│   └── vllm_service/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: запуск vLLM server + wrapper API
│       ├── config.py               # Параметры моделей, GPU, LoRA
│       │
│       ├── server/
│       │   ├── __init__.py
│       │   ├── launcher.py         # Запуск vLLM AsyncLLMEngine
│       │   └── health.py           # Health probes
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py           # FastAPI router (прокси + кастомные эндпоинты)
│       │   ├── completions.py      # /v1/completions
│       │   ├── chat.py             # /v1/chat/completions
│       │   └── models.py           # /v1/models, /v1/lora
│       │
│       ├── lora/
│       │   ├── __init__.py
│       │   ├── manager.py          # Управление LoRA-адаптерами
│       │   └── registry.py         # Реестр доступных адаптеров
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── metrics.py          # Prometheus metrics
│           └── tracing.py          # OpenTelemetry
│
├── models/                         # Локальное хранилище моделей (volume mount)
│   └── .gitkeep
│
├── lora_adapters/                  # Локальное хранилище LoRA (volume mount)
│   └── .gitkeep
│
└── tests/
    ├── conftest.py
    ├── test_api.py
    └── test_lora.py
```

---

## Triton Inference

```
triton_inference/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile                      # На основе nvcr.io/nvidia/tritonserver
├── README.md
│
├── src/
│   └── triton_service/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: запуск Triton + wrapper
│       ├── config.py               # Конфигурация моделей, батчинга
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py           # FastAPI wrapper для кастомных эндпоинтов
│       │   ├── detect.py           # Эндпоинт детекции
│       │   ├── track.py            # Эндпоинт трекинга
│       │   └── health.py           # Health probes
│       │
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── triton_grpc.py      # tritonclient gRPC wrapper
│       │   └── triton_http.py      # tritonclient HTTP wrapper
│       │
│       ├── preprocessing/
│       │   ├── __init__.py
│       │   ├── image.py            # Предобработка изображений
│       │   └── video.py            # Предобработка видео
│       │
│       ├── postprocessing/
│       │   ├── __init__.py
│       │   ├── nms.py              # Non-Maximum Suppression
│       │   ├── tracking.py         # ByteTrack/DeepSORT postprocessing
│       │   └── visualization.py    # Рисование bbox, масок
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── metrics.py
│           └── tracing.py
│
├── model_repository/               # Triton model repository (volume mount)
│   ├── yolo_detector/
│   │   ├── config.pbtxt
│   │   └── 1/
│   │       └── model.onnx
│   ├── bytetrack/
│   │   ├── config.pbtxt
│   │   └── 1/
│   │       └── model.onnx
│   └── ensemble_detect_track/
│       └── config.pbtxt
│
├── scripts/
│   ├── convert_model.py            # Конвертация моделей в ONNX/TensorRT
│   └── benchmark.py                # Бенчмарк производительности
│
└── tests/
    ├── conftest.py
    ├── test_detection.py
    └── test_tracking.py
```

---

## SmolVLA Service

```
smolvla_service/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile                      # GPU-образ для cloud-версии
├── README.md
│
├── src/
│   └── smolvla_service/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: gRPC server + health
│       ├── config.py
│       │
│       ├── server/
│       │   ├── __init__.py
│       │   ├── grpc_server.py      # gRPC servicer для VLA inference
│       │   └── health.py
│       │
│       ├── inference/
│       │   ├── __init__.py
│       │   ├── smolvla.py          # SmolVLA model loader + inference
│       │   ├── xvla.py             # X-VLA model loader + inference
│       │   └── action_chunking.py  # Action chunk generation + smoothing
│       │
│       ├── training/
│       │   ├── __init__.py
│       │   ├── fine_tuner.py       # Fine-tuning pipeline
│       │   ├── dataset.py          # LeRobot dataset loader
│       │   └── evaluator.py        # Оценка качества модели
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── metrics.py
│           └── tracing.py
│
├── models/                         # Локальное хранилище моделей (volume mount)
│   └── .gitkeep
│
└── tests/
    ├── conftest.py
    ├── test_inference.py
    └── test_action_chunking.py
```

---

## Communication Service

```
communication_service/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── README.md
│
├── src/
│   └── comm_service/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: bridge + health API
│       ├── config.py
│       │
│       ├── bridge/
│       │   ├── __init__.py
│       │   ├── mqtt_to_rabbitmq.py # Мост MQTT → RabbitMQ (uplink)
│       │   ├── rabbitmq_to_mqtt.py # Мост RabbitMQ → MQTT (downlink)
│       │   └── router.py           # Правила маршрутизации между протоколами
│       │
│       ├── mqtt/
│       │   ├── __init__.py
│       │   ├── client.py           # paho-mqtt client wrapper
│       │   ├── topics.py           # Реестр MQTT-топиков и их схемы
│       │   └── acl.py              # Правила ACL для MQTT
│       │
│       ├── rabbitmq/
│       │   ├── __init__.py
│       │   ├── client.py           # pika client wrapper
│       │   ├── exchanges.py        # Декларация exchanges
│       │   ├── queues.py           # Декларация queues
│       │   └── consumers.py        # Consumer registry
│       │
│       └── monitoring/
│           ├── __init__.py
│           ├── metrics.py
│           └── health.py           # Health checks для EMQX и RabbitMQ
│
├── config/
│   ├── emqx/
│   │   ├── emqx.conf              # Конфигурация EMQX
│   │   ├── acl.conf                # ACL-правила
│   │   └── auth-mnesia.conf       # Аутентификация
│   └── rabbitmq/
│       ├── rabbitmq.conf
│       ├── definitions.json        # Предварительные exchanges, queues, bindings
│       └── enabled_plugins
│
└── tests/
    ├── conftest.py
    ├── test_bridge.py
    ├── test_mqtt_client.py
    └── test_rabbitmq_client.py
```

---

## Robot Edge

```
robot_edge/
├── .env.example
├── .env
├── .gitignore
├── .python-version                 # 3.11
├── .pre-commit-config.yaml
├── poetry.toml
├── pyproject.toml
├── poetry.lock
├── Dockerfile                      # На основе osrf/ros:jazzy-desktop-full + JetPack
├── Dockerfile.vnc                  # С VNC для отладки визуализации
├── docker-compose.edge.yml         # Compose для Edge-стека (все контейнеры на Jetson)
├── README.md
│
├── src/
│   └── robot_edge/
│       ├── __init__.py
│       ├── main.py                 # Entrypoint: запуск ROS2 node + bridge
│       ├── config.py
│       │
│       ├── bridge/
│       │   ├── __init__.py
│       │   ├── ros2_mqtt_bridge.py # ROS2 ↔ MQTT трансляция
│       │   ├── topic_mapper.py     # Маппинг ROS2 topic → MQTT topic
│       │   └── serializer.py       # ROS2 msg ↔ JSON/Protobuf конвертация
│       │
│       ├── ai_proxy/
│       │   ├── __init__.py
│       │   ├── proxy.py            # Edge AI Proxy — маршрутизация inference
│       │   ├── model_manager.py    # Загрузка/обновление локальных моделей
│       │   ├── fallback.py         # Cloud ↔ Edge fallback логика
│       │   └── cache.py            # Локальный кэш результатов
│       │
│       ├── smolvla_edge/
│       │   ├── __init__.py
│       │   ├── inference.py        # SmolVLA Edge inference (ONNX/TensorRT)
│       │   └── action_executor.py  # Исполнение action chunks
│       │
│       ├── autonomy/
│       │   ├── __init__.py
│       │   ├── offline_mode.py     # Логика автономной работы при потере связи
│       │   ├── safety_monitor.py   # Watchdog, e-stop, ограничения
│       │   ├── buffer.py           # Буферизация телеметрии и событий
│       │   └── sync.py             # Синхронизация при восстановлении связи
│       │
│       ├── ros2/
│       │   ├── __init__.py
│       │   ├── nodes/
│       │   │   ├── __init__.py
│       │   │   ├── telemetry_node.py   # Публикация телеметрии
│       │   │   ├── command_node.py     # Приём и выполнение команд
│       │   │   └── sensor_node.py      # Чтение сенсоров (камеры, LiDAR, IMU)
│       │   └── launch/
│       │       └── edge_launch.py      # ROS2 launch файл
│       │
│       └── monitoring/
│           ├── __init__.py
│           └── metrics.py          # Локальные метрики (CPU, GPU, температура)
│
├── models/                         # Локальные модели (volume mount)
│   └── .gitkeep
│
└── tests/
    ├── conftest.py
    ├── test_bridge.py
    ├── test_ai_proxy.py
    └── test_autonomy.py
```

---

## Frontend

```
frontend/
├── .env.example
├── .env
├── .gitignore
├── .eslintrc.cjs
├── .prettierrc
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── package.json
├── package-lock.json
├── Dockerfile
├── nginx.conf                      # Nginx для production serving
├── README.md
│
├── public/
│   ├── favicon.ico
│   ├── robots.txt
│   └── assets/
│       ├── models/                 # 3D-модели роботов (.glb/.gltf)
│       └── icons/
│
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── vite-env.d.ts
│   │
│   ├── api/
│   │   ├── client.ts              # Axios / fetch wrapper
│   │   ├── ws.ts                  # WebSocket client
│   │   ├── robots.ts              # Robot API calls
│   │   ├── tasks.ts               # Task API calls
│   │   ├── auth.ts                # Auth API calls
│   │   └── telemetry.ts           # Telemetry API calls
│   │
│   ├── store/
│   │   ├── index.ts               # Zustand / Redux store
│   │   ├── robotStore.ts
│   │   ├── taskStore.ts
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   │
│   ├── pages/
│   │   ├── Dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── RobotList.tsx
│   │   │   ├── TaskBoard.tsx
│   │   │   └── MetricsPanel.tsx
│   │   ├── Chat/
│   │   │   ├── ChatPage.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── ChatInput.tsx
│   │   ├── Visualization/
│   │   │   ├── Scene3D.tsx
│   │   │   ├── RobotModel.tsx
│   │   │   ├── EnvironmentMap.tsx
│   │   │   └── CameraControls.tsx
│   │   ├── Admin/
│   │   │   ├── AdminPage.tsx
│   │   │   ├── UserManagement.tsx
│   │   │   └── SystemConfig.tsx
│   │   └── Auth/
│   │       ├── LoginPage.tsx
│   │       └── RegisterPage.tsx
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── Robot/
│   │   │   ├── RobotCard.tsx
│   │   │   ├── RobotStatus.tsx
│   │   │   └── RobotDetail.tsx
│   │   ├── Task/
│   │   │   ├── TaskCard.tsx
│   │   │   └── TaskDetail.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Modal.tsx
│   │       ├── Table.tsx
│   │       └── Loader.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useAuth.ts
│   │   ├── useRobots.ts
│   │   └── useTelemetry.ts
│   │
│   ├── types/
│   │   ├── robot.ts
│   │   ├── task.ts
│   │   ├── user.ts
│   │   └── telemetry.ts
│   │
│   ├── utils/
│   │   ├── formatters.ts
│   │   ├── constants.ts
│   │   └── validators.ts
│   │
│   └── styles/
│       ├── globals.css
│       └── theme.ts
│
└── tests/
    ├── setup.ts
    ├── components/
    └── pages/
```

---

## Data Storage (инфраструктурный модуль)

Не является отдельным микросервисом. Конфигурации и миграции хранятся в корневом репозитории.

```
infrastructure/
├── db/
│   ├── postgres/
│   │   ├── init.sql                # Начальная инициализация
│   │   └── migrations/             # Alembic (управляется из Orchestrator)
│   ├── influxdb/
│   │   ├── init.sh                 # Создание buckets, tokens
│   │   └── telegraf.conf           # Если используется Telegraf
│   ├── neo4j/
│   │   ├── init.cypher             # Начальные constraints и indexes
│   │   └── plugins/                # APOC и др. плагины
│   ├── redis/
│   │   ├── redis.conf              # Конфигурация Redis Stack
│   │   └── modules.conf            # RedisJSON, RediSearch, RedisTimeSeries
│   └── minio/
│       ├── init.sh                 # Создание бакетов и политик
│       └── policies/               # JSON-политики доступа
```
