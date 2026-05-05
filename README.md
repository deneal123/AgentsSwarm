# Документация: AgentsSwarm

## Официальное название:

> Организация кооперативного восприятия сцены в группе автономных агентов на основе обмена визуальной информацией (Cooperative Visual Perception in Multi-Agent Systems)

## Рабочее название:

> Автономный рой роботов - (AgentsSwarm)

## Компоненты архитектуры системы

- [interface](https://github.com/deneal123/AgentsSwarm/tree/interface)
- [isaac_mission_control+mcp_server](https://github.com/deneal123/AgentsSwarm/tree/isaac_mission_control)
- [isaac_mission_dispatch+msp_server](https://github.com/deneal123/AgentsSwarm/tree/isaac_mission_dispatch)
- [nvidia_isaac_simulation](https://github.com/deneal123/AgentsSwarm/tree/nvidia_isaac_simulation)
- [orchestrator](https://github.com/deneal123/AgentsSwarm/tree/orchestrator)
- [smolvla_tools](https://github.com/deneal123/AgentsSwarm/tree/smolvla_tools)
- [vllm_service](https://github.com/deneal123/AgentsSwarm/tree/vllm_service)
- [workspace_isaac_simulation](https://github.com/deneal123/AgentsSwarm/tree/workspace_isaac_simulation)


## TODO:

### 1. NVIDIA Isaac Sim

Открытая платформа для разработки роботов и создания симуляций.

#### 1.1 Подготовка окружения
- [x] Подготовка workspace в Docker контейнере с собранным ROS 2 Jazzy под Ubuntu 24.04 для разработки и использования ROS 2 launch файлов (включая поднятие ROS 2 bridge для публикации данных из Isaac Sim)

#### 1.2 Запуск симуляции
- [x] Подготовка Docker Compose конфигурации для запуска NVIDIA Isaac Sim в headless режиме с Web-based viewer для удаленного доступа к интерфейсу

#### 1.3 Настройка сцены
- [x] Создание сцены (или поиск из готовых ассетов/сценариев), настройка сцены и Action Graph роботов (namespaces)

#### 1.4 Проверка данных
- [x] Проверка работоспособности публикации данных из Isaac Sim в ROS 2 топики

#### 1.5 Isaac ROS Mission Client
- [x] Запуск из workspace пакета `isaac_ros_mission_client` (VDA5050) для сбора и преобразования данных из симулятора в ROS 2 топики
- [x] Подготовка конфигурации запуска команд для нескольких роботов
- [x] Генерация occupancy map и `.yaml` конфигураций

#### 1.6 Isaac ROS Cloud Control
- [x] Проверка работоспособности пакета `isaac_ros_cloud_control` в собранном workspace
- [x] Подготовка ROS 2 команд для запуска клиента с несколькими роботами

---

### 2. MissionDispatch + MissionControl

#### Описание компонентов
- **Mission Dispatch**: VDA5050-совместимый облачный сервис для отправки миссий одному или нескольким роботам
- **Mission Control**: Сервис построения дерева поведения задач. Использует occupancy map, строит граф карты, подбирает оптимальные маршруты (с использованием cuOpt) и делегирует выполнение через Mission Dispatch с VDA5050 Mission Client

#### 2.1 Развертывание
- [x] Подготовка Docker Compose конфигурации с dev-контейнерами и окружением для запуска MissionDispatch и MissionControl
- [x] Компоненты: cuOpt, Mosquitto, PostgreSQL, mission-database, mission-dispatch, wpg, mission-control, waypoint_ui

#### 2.2 Багфиксы и доработки
- [x] **Исправление endpoint'ов**: обнаружено использование несуществующего endpoint `push_map`, замена на актуальные методы mission_control: `map/update_robot`, `map/metadata`
- [x] Создан форк с корректировками, в планах — создание Pull Request в официальный репозиторий NVIDIA
- [x] **Исправление импорта Pydantic**: обнаружена ошибка импорта, из-за которой падал waypoint_ui (необходим для быстрой проверки и получения координат для миссии по occupancy map)

#### 2.3 Тестирование
- [x] Запуск и проверка работоспособности подключения сервисов
- [x] Проверка создания и инициализации конфигураций роботов
- [x] Проверка доставки данных от `vda5050_client_bringup` из workspace до сервисов
- [x] Подтверждение статуса "online" для роботов
- [x] Пробный запуск миссии через MissionDispatch Swagger, проверка перехода миссии в статус "running"
- [x] Проверка получения координат для миссии через waypoint_ui

#### 2.4 Интеграция

#NOTE: Возникла проблема с состояниями роботов, не происходит инициализация стартового положения робота, не публикуются данные odom
- [?] Проверка корректного построения дерева поведения в MissionControl и передачи миссий роботам

---

### 3. Связка NVIDIA Isaac Sim ↔ MissionDispatch + MissionControl

- [?] Проверка корректности настройки связки: NVIDIA Isaac Sim ↔ ROS 2 bridge ↔ workspace
- [?] Проверка, что Mission Client получает корректные данные от симуляции и обновляет состояние роботов в связке с MissionDispatch
- [?] Проверка, что созданные деревья поведения в MissionControl успешно исполняются роботами в NVIDIA Isaac Sim

---

### 4. MCP Server (Model Context Protocol)

**RosMSPServer + DispatchMCPServer + ControlMCPServer**

MCP — протокол, служащий посредником между LLM и внешними данными/инструментами.

#### 4.1 Развертывание
- [x] Подготовка Docker Compose конфигурации с контейнерами для использования MCP протоколов
- [x] Обеспечение взаимодействия между MissionDispatch, MissionControl, ROS 2 и агентом для передачи управления роботами LLM

#### 4.2 Доработка
- [?] Доработка существующих MCP протоколов для MissionDispatch и MissionControl
- [?] Отключение лишних инструментов
- [?] Добавление кастомных инструментов для специфичных задач

#### 4.3 Интеграция
- [x] Проверка подключения LLM к разработанным MCP протоколам

---

### 5. vLLM Service

Микросервис на фреймворке vLLM для сервинга LLM моделей в OpenAI-compatible формате в data parallel режиме на двух нодах.

#### 5.1 Разработка
- [x] Подготовка шаблонной структуры микросервиса
- [x] Реализация основных API endpoints для взаимодействия с LLM
- [x] Подготовка Docker Compose конфигурации

#### 5.2 Запуск моделей
- [x] Сервинг модели **Qwen-Instruct Agent Tool** для выполнения агентских задач

#### 5.3 Тестирование
- [x] Тестирование и проверка работы модели в data parallel режиме

---

### 6. Orchestrator

Микросервис на базе **OpenAI Agents SDK**, выступающий интеллектуальной прослойкой между пользователем и инфраструктурой управления роботами. Orchestrator принимает запросы на естественном языке, маршрутизирует их к специализированным агентам, вызывает инструменты через MCP-серверы (RosMSP, MissionControl, MissionDispatch) и возвращает результат в реальном времени.

#### 6.1 Базовая настройка и окружение
- [x] Создание базовой структуры микросервиса на FastAPI
- [x] Настройка Dockerfile и Docker Compose конфигурации
- [x] Конфигурация переменных окружения (.env) для подключения к MCP-серверам
- [x] Интеграция с Redis для управления сессиями и кэширования

#### 6.2 MCP-серверы и инструменты
- [x] Подключение RosMSP MCP сервера (конфигурация + env)
- [x] Подключение MissionControl MCP сервера (конфигурация + env)
- [x] Подключение MissionDispatch MCP сервера (конфигурация + env)
- [x] Контейнеризация ros-msp: Dockerfile, pyproject.toml, requirements/, переименование docker/ros_mcp → docker/ros-msp
- [x] SSE-транспорт для всех трёх MCP-серверов (docker-compose dev: порты 8010/8011/8012)
- [x] Переменные среды: ROSBRIDGE_IP, ROSBRIDGE_PORT, ROS_MSP_TRANSPORT, ROS_MSP_MCP_URL
- [x] Динамический выбор транспорта stdio/sse через env vars (`mcp.py` → `_server_config()`)
- [x] RobotInfo: добавлен mission_dispatch_server() (без него агент не имел доступа к fleet summary / battery)

#### 6.3 Агентная архитектура

##### RouterAgent
- [x] Разработка system prompt для маршрутизации запросов
- [x] Реализация handoff логики между специализированными агентами (конфигурация)
- [x] Добавление fallback агента для общих вопросов
- [x] Тестирование корректности маршрутизации (смоук-набор для классификации)

##### MissionPlannerAgent (новый)
- [x] Скелет планировщика: детерминированный план, цикл шагов, стрим событий/статуса
- [x] Двухфазный агент: построение плана из шагов по сложному запросу
- [x] Замкнутый цикл: выполнение шагов через handoff к специализированным агентам до успеха/остановки/ошибки
- [x] Стриминг шагов и повторное планирование при проблемах
- [x] Контракты шагов плана (meta: expected_outcome, tools, depends_on, inputs)
- [x] Хьюристика выбора агента: Navigation для одиночных задач, SwarmCoordinator при упоминании нескольких роботов/ключевых слов, прокидывание target_robots в meta
- [x] Исправление инструментов в meta шагов плана: реальные имена MCP-инструментов (submit_navigation_mission, dispatch_mission, get_mission_status, get_idle_robots, check_robot_health)
- [x] `POST /task/{task_id}/replan` — пересборка плана с опциональным немедленным запуском (`?run=true`)

###### Интеграция с OpenAI Agents SDK (по примерам из docs/open-agents-sdk и docs/example)
- [x] Подключить реальный Agents SDK Runner вместо симулятора (streamed run + handoff) для плановых шагов
- [x] Использовать фабрику клиентов (`services/openai_client.py`) для переключения OpenAI/vLLM через переменные окружения
- [x] Внедрить Router на Agents SDK с `Runner.run_streamed` (ранний вывод категории) и схемой output_type для маршрутизации
- [x] Добавить guardrails/validators на вход/выход (см. `docs/example/guardrail.py`, `guide.md`)
- [x] Применить pydantic output_type для структурированных ответов (e.g. `RoutingDecision`, `UserContext`)
- [x] Прокинуть ModelSettings/RunConfig в раннеры (temperature/top_p, nest_handoff_history) и чтение моделей из env
- [x] Подключить tools/модели через MCP/Agents SDK registry (см. `tools.md`, `msp.md`) для реальных вызовов MissionControl/MissionDispatch

##### RobotInfoAgent

- [x] Реализация агента с подключением RosMSP MCP + MissionDispatch MCP (оба необходимы)
- [x] Разработка system prompt с инструкциями по работе с роботами (два блока: Mission Dispatch + ros-msp)
- [x] Добавление логики обработки запросов о состоянии роботов (get_fleet_summary, get_robot_status, check_robot_health)
- [x] Реализация batch запросов для получения информации о всех роботах (get_idle_robots, get_mission_status)
- [x] Обработка edge cases: робот не найден, недоступен

##### NavigationAgent
- [x] Реализация агента с подключением MissionControl и MissionDispatch MCP (конфигурация)
- [x] Разработка system prompt для навигационных задач (обязательный 3-шаговый алгоритм)
- [x] Реализация логики создания и отправки миссий (submit_navigation_mission, dispatch_mission)
- [x] Закрыта дыра мониторинга: обязательный polling get_mission_status до COMPLETED/FAILED (до 8 проверок)
- [x] Сценарии: зарядка (submit_charging_mission), отстыковка (submit_undock_mission), прямое управление (dispatch_mission)

##### SwarmCoordinatorAgent
- [x] Реализация агента с подключением всех трех MCP-серверов (конфигурация)
- [x] Разработка system prompt для координации нескольких роботов (обязательный 4-шаговый алгоритм)
- [x] Реализация логики распределения задач: поиск свободных роботов, health-check, параллельная отправка миссий
- [x] Мониторинг роя: поочерёдный polling get_mission_status для каждого робота (до 6 раундов)
- [?] Добавление алгоритмов для точки встречи (rendezvous) на стороне агента (инструкции есть, LLM вычисляет)
- [?] Реализация балансировки нагрузки между роботами

#### 6.4 Потоковая обработка (Streaming)

- [x] Реализация StreamCollector для агрегации логов и событий (скелет)
- [x] Форматирование стримов с указанием task_id и source (payload с ts/meta/level)
- [x] Добавление метаданных в стримы: timestamp, уровень логирования, тип события
- [x] Реализация буферизации для поздних подключений (seq + get_since, cap)
- [x] HTTP endpoint `/task/{task_id}/events` для выборки стрима (REST-заглушка до WebSocket)
- [x] HTTP endpoint `POST /task/{task_id}/events` для приема событий/логов от внешних воркеров с опциональным обновлением статуса
- [x] Стрим событий отмены (`Task canceled`, `Task canceled during execution`) и маркировка плана как `canceled`
- [x] WebSocket `/ws/task/{task_id}` для стриминга событий (пуллинг StreamCollector)

#### 6.5 Управление сессиями и контекстом

- [x] Настройка Redis для хранения сессий
- [x] Реализация SessionManager с методами:
  - `get_session(task_id)` — получение контекста сессии
  - `update_session(task_id, context)` — обновление контекста
  - `clear_session(task_id)` — очистка сессии
- [x] Хранение истории запросов для диалогового контекста
- [x] Сохранение последнего использованного robot_id
- [x] Кэширование результатов MCP вызовов

#### 6.6 Обработка ошибок и fallback

- [x] Реализация глобального exception handler
- [x] Graceful shutdown при отключении MCP-серверов (lifespan hooks)
- [x] Retry механизм для временных сбоев MCP (sync/async backoff утилита)
- [x] Логирование ошибок с контекстом task_id
- [x] Отправка пользователю понятных сообщений об ошибках через WebSocket

#### 6.7 API эндпоинты

- [x] `POST /task` — прием задачи от Worker
  - Input: `{task_id: str, prompt: str, session_data: Optional[dict]}` + query `run=false` для отложенного запуска
  - Output: `{status: "processing"|"pending", task_id: str}`
- [x] `GET /task/{task_id}/status` — получение статуса задачи
- [x] `GET /task/{task_id}/plan` — получение плана шагов (если построен)
- [x] `GET /task/{task_id}/logs` — получение всех логов задачи
- [x] `POST /task/{task_id}/cancel` — отмена выполнения задачи
- [x] `POST /task/{task_id}/events` — приём событий (stream) и обновлений статуса от воркеров/агентов
- [x] `GET /health` — healthcheck эндпоинт
- [x] `POST /task/{task_id}/run` — запуск отложенной задачи (Router/Planner) с построением плана и стримингом шагов
- [x] `POST /task/{task_id}/cancel` — прерывает исполнение, помечает шаги плана `canceled`, стримит события отмены
- [x] `POST /task/{task_id}/replan` — пересборка плана; `?run=true` — сразу запустить

#### 6.8 Качество кода и рефакторинг

- [x] Фикс `BackgroundTasks | None` → `BackgroundTasks = BackgroundTasks()` (FastAPI DI несовместим с union-типом)
- [x] Фикс `Iterable` → `tuple` для exceptions в `retry.py`
- [x] Предкомпиляция regex в `planner.py` (`_ROBOT_ID_RE`, `_GOAL_SPLIT_RE`) — вынос из hot path
- [x] Упрощение `_extract_robot_ids()` через `dict.fromkeys()` вместо ручной дедупликации
- [x] Замена `os.getenv("AGENTS_TRACING_DISABLED", "1") != "0"` на `env_bool()` в `agents_sdk.py`
- [x] Консолидация трёх дублирующихся MCP-фабрик в единый `_server_config()` в `mcp.py`

#### 6.9 Тестирование

- [x] Юнит-тесты для базовых сервисов (health, sessions, streaming, retry, события, заглушечный раннер)
- [x] Контрактные тесты планировщика (агент, инструменты, target_robots, зависимости шагов)
- [x] Тесты guardrails (input/output валидация, категории роутера, silent fallback)
- [x] Интеграционные тесты HTTP API (run, cancel, replan, events, WebSocket) — 43/43 ✅
- [?] Интеграционные тесты с реальными MCP-серверами (требуют Docker-окружения)
- [?] E2E тесты полного цикла с LLM (требуют работающей модели)
- [?] Тесты потоковой передачи данных через WebSocket (async client)
- [?] Нагрузочное тестирование (100+ параллельных задач)

#### 6.10 Документация

- [x] README полностью переписан: удалён Gateway, актуальная архитектура с Interface-сервисом
- [x] Архитектурная диаграмма Mermaid — актуальная топология (5 сервисов + rosbridge + Isaac Sim)
- [x] Таблица fallback-ов и устойчивости
- [x] Инвентарь MCP-инструментов по каждому серверу
- [x] Примечание об ограничении: оркестратор не поллирует миссии автоматически (это задача агента)

#### 6.11 Интеграция с Interface

- [?] Тестирование эндпоинта `/task` с реальным интерфейсом
- [?] Тестирование стримов от Orchestrator до Frontend

---

### 7. Interface

#### 7.1 Базовая настрока и окружение

- ...

### 7.2 Агентная архитектура для сбора мутимодального контекста

- ...

### 7.3 Реализованные ендпоинты бекенда

- ...

### 7.4 Реализация фронтенда

- ...

---

### 8. SmolVLA Tools

Фреймворк для оптимизации моделей SmolVLA (Vision‑Language‑Action) для робототехнических приложений. Реализует полный пайплайн сжатия: дистилляция знаний → FP16 pruning → анализ квантизации. Итоговая модель сохраняет >90% точности при сжатии в 443 раза (1.7 ГБ → <0.5 ГБ VRAM) и ускорении инференса 20–25×, что позволяет развертывать её на борту робота (Jetson Orin Nano).

#### 8.1 Подготовка окружения и инструментов

- [x] Настройка проекта с uv и pyproject.toml
- [x] Интеграция с HuggingFace (lerobot/smolvla_base, lerobot/pusht, lerobot/libero)
- [x] Подготовка .env.example и конфигурации переменных окружения
- [x] Создание шаблонов скриптов: train.py, export_onnx.py

#### 8.2 Архитектура и модели

- [x] Реализация TeacherModel с загрузкой предобученных весов
- [x] Реализация StudentModel с настраиваемым коэффициентом сжатия (student_ratio)
- [x] Разработка многокомпонентной функции потерь дистилляции (MSE + KL + attention transfer)
 Поддержка mixed precision (FP16) через torch.cuda.amp

#### 8.3 Пайплайн оптимизации

- [x] Stage 1: Knowledge distillation (10 эпох, температура 3.0, alpha 0.7)
- [x] Stage 2: Mixed precision inference (FP16) для ускорения на тензорных ядрах
- [x] Stage 3: Structured pruning (30% весов в Linear слоях)
- [x] Stage 4: Анализ квантизации (INT8) с выявлением критических слоёв

#### 8.4 Эксперименты и валидация

- [x] Валидация Teacher‑модели на lerobot/libero: MSE 0.1782, R² 0.8412
- [x] Запуск полного пайплайна на 10 эпохах
- [x] Сбор метрик: MSE (+9.1%), MAE (+5.1%), R² (–1.8%)
- [x] Измерение сжатия: 443× по параметрам, 12× по VRAM
- [x] Оценка per‑action MAE (7 действий манипулятора) — разница в третьем знаке

#### 8.5 Профилирование и бенчмарки

- [x] Профилирование времени инференса (batch=1) на RTX 4090
- [x] Сравнение latency: Teacher → 450 ms, Student → 18 ms (25× ускорение)
- [x] Анализ потребления памяти: Teacher (FP32) → 6 GB, Student (FP16) → <0.5 GB

### 8.6 Экспорт и развертывание

- [x] Экспорт Student‑модели в ONNX (фиксированный вход 224×224)
- [x] Проверка совместимости с NVIDIA TensorRT (рекомендован FP16 режим)
- [x] Подготовка примеров инференса для встраиваемых платформ

#### 8.7 Документация и отчёты

- [x] Оформление отчётов №1–3 (docs/report_1.md, report_2.md, report_3.md)
- [x] Написание README с примерами использования и результатами
- [x] Фиксация инженерных выводов для интеграции в рой (Jetson‑совместимость)

### 9. Доработка workspace, разработка VDA5050 адаптер хендлера для создания кастомного action действия для использования VLA в миссиях (интеграция SmolVLA в MissionDispatch+MissionControl через кастомные действия) - добавляет индивидуальную автономность

#### 9.1 В разработке ...

---

## Технические требования для запуска полного стека проекта

- Машина для симуляций (Selectel)
  - **Образ**: Ubuntu 24.04 LTS 64-bit GPU driver 580 Open
  - **Конфигурация**: 4 vCPU, 16 GB RAM, RTX 4090 (24 GB VRAM)
  - **Диск**: 128 GB
  - **Стоимость**: 15 012,70 ₽/мес
- Машина для микросервисов (Selectel)
  - **Образ**: Ubuntu 24.04 LTS 64-bit
  - **Конфигурация**: 4 vCPU, 8 GB RAM
  - **Диск**: 128 GB
  - **Стоимость**: 1 156,09 ₽/мес
- Кластер для LLM (MTS)
  - **Образ**: Ubuntu 24.04 LTS 64-bit
  - **Конфигурация**: 2 ноды × Tesla V100-PCIE (32 GB VRAM)
  - **Диск**: 2 ноды x 1.6 ТБ
  - **Стоимость**: Бесплатно
- Итого
  | Параметр | Значение |
  |---------|---------|
  | Общая стоимость | **16 168,79 ₽/мес** |


## Sourses

- [x] [vLLM Server](https://github.com/vllm-project/vllm)
- [x] [Ros2](https://github.com/ros2)
- [x] [Redis](https://redis.readthedocs.io/en/stable/index.html)
- [x] [RabbitMQ](https://www.rabbitmq.com/tutorials/tutorial-one-python)
- [x] [PostgreSQL](https://www.geeksforgeeks.org/python/sqlalchemy-tutorial-in-python/)
- [x] [Minio](https://docs.min.io/enterprise/aistor-object-store/developers/sdk/python/)
- [x] [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [x] [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [x] [RosMspServer](https://github.com/robotmcp/ros-mcp-server.git)
- [x] [RosMspClient](https://github.com/robotmcp/robotmcp_client.git)
- [x] [NVIDIA Isaac ROS](https://nvidia-isaac-ros.github.io/getting_started/index.html#system-requirements)
- [x] [NVIDIA Isaac ROS Repositories and Packages](https://nvidia-isaac-ros.github.io/repositories_and_packages/index.html)
- [x] [Multiple Robot ROS Navigation](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/ros_tutorials/tutorial_ros_multi_navigation.html)
- [x] [Nvidia Vss Agent](https://docs.nvidia.com/vss/3.1.0/quickstart.html)
- [x] [Nvidia Agent Workflows](https://docs.nvidia.com/vss/latest/adding-workflows.html)
- [x] [video-search-and-summarization](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization/tree/main)
- [x] [huggingface.co/lerobot/smolvla_base](https://huggingface.co/lerobot/smolvla_base)
- [x] [arxiv.org/abs/2506.01844](https://arxiv.org/abs/2506.01844)
- [x] [github.com/huggingface/lerobot](https://github.com/huggingface/lerobot)
- [x] [huggingface.co/docs/lerobot](https://huggingface.co/docs/lerobot)
