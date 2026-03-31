# Документация: AgentsSwarm

## Официальное название:

> Организация кооперативного восприятия сцены в группе автономных агентов на основе обмена визуальной информацией (Cooperative Visual Perception in Multi-Agent Systems)

## Рабочее название:

> Автономный рой роботов - (AgentsSwarm)

## Компоненты архитектуры системы

- [data_storage_service](https://github.com/deneal123/AgentsSwarm/tree/data_storage_service)
- [frontend](https://github.com/deneal123/AgentsSwarm/tree/frontend)
- [gateway](https://github.com/deneal123/AgentsSwarm/tree/gateway)
- [isaac_mission_control+mcp_server](https://github.com/deneal123/AgentsSwarm/tree/isaac_mission_control)
- [isaac_mission_dispatch+msp_server](https://github.com/deneal123/AgentsSwarm/tree/isaac_mission_dispatch)
- [isaac_ros_server](https://github.com/deneal123/AgentsSwarm/tree/isaac_ros_server)
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

### 4. Isaac Ros Server (Model Context Protocol)

**RosMSPServer + DispatchMCPServer + ControlMCPServer**

MCP — протокол, служащий посредником между LLM и внешними данными/инструментами.

#### 4.1 Развертывание
- [?] Подготовка Docker Compose конфигурации с контейнерами для использования MCP протоколов
- [?] Обеспечение взаимодействия между MissionDispatch, MissionControl, ROS 2 и агентом для передачи управления роботами LLM

#### 4.2 Доработка
- [?] Доработка существующих MCP протоколов для MissionDispatch и MissionControl
- [?] Отключение лишних инструментов
- [?] Добавление кастомных инструментов для специфичных задач

#### 4.3 Интеграция
- [?] Проверка подключения LLM к разработанным MCP протоколам

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
- [ ] Создание базовой структуры микросервиса на FastAPI
- [ ] Настройка Dockerfile и Docker Compose конфигурации
- [ ] Конфигурация переменных окружения (.env) для подключения к MCP-серверам
- [ ] Интеграция с Redis для управления сессиями и кэширования

#### 6.2 MCP-серверы и инструменты
- [ ] Подключение RosMSP MCP сервера с ? инструментами.
- [ ] Подключение MissionControl MCP сервера с 12 инструментами.
- [ ] Подключение MissionDispatch MCP сервера с 17 инструментами:

#### 6.3 Агентная архитектура

##### RouterAgent
- [ ] Разработка system prompt для маршрутизации запросов
- [ ] Реализация handoff логики между специализированными агентами
- [ ] Добавление fallback агента для общих вопросов
- [ ] Тестирование корректности маршрутизации

##### RobotInfoAgent
- [ ] Реализация агента с подключением RosMSP MCP
- [ ] Разработка system prompt с инструкциями по работе с роботами
- [ ] Добавление логики обработки запросов о состоянии роботов
- [ ] Реализация batch запросов для получения информации о всех роботах
- [ ] Обработка edge cases: робот не найден, недоступен

##### NavigationAgent
- [ ] Реализация агента с подключением MissionControl и MissionDispatch MCP
- [ ] Разработка system prompt для навигационных задач
- [ ] Интеграция с cuOpt для построения маршрутов
- [ ] Реализация логики создания и отправки миссий
- [ ] Добавление подтверждения выполнения миссии

##### SwarmCoordinatorAgent
- [ ] Реализация агента с подключением всех трех MCP-серверов
- [ ] Разработка system prompt для координации нескольких роботов
- [ ] Реализация логики распределения задач между роботами
- [ ] Добавление алгоритмов для точки встречи (rendezvous)
- [ ] Реализация балансировки нагрузки между роботами

#### 6.4 Потоковая обработка (Streaming)

- [ ] Реализация StreamCollector для агрегации логов и событий
- [ ] Интеграция с WebSocket Manager Gateway для передачи потоков
- [ ] Форматирование стримов с указанием task_id и source
- [ ] Добавление метаданных в стримы: timestamp, уровень логирования, тип события
- [ ] Реализация буферизации для поздних подключений

#### 6.5 Управление сессиями и контекстом

- [ ] Настройка Redis для хранения сессий
- [ ] Реализация SessionManager с методами:
  - `get_session(task_id)` — получение контекста сессии
  - `update_session(task_id, context)` — обновление контекста
  - `clear_session(task_id)` — очистка сессии
- [ ] Хранение истории запросов для диалогового контекста
- [ ] Сохранение последнего использованного robot_id
- [ ] Кэширование результатов MCP вызовов

#### 6.6 Обработка ошибок и fallback

- [ ] Реализация глобального exception handler
- [ ] Graceful shutdown при отключении MCP-серверов
- [ ] Retry механизм для временных сбоев MCP
- [ ] Логирование ошибок с контекстом task_id
- [ ] Отправка пользователю понятных сообщений об ошибках через WebSocket

#### 6.7 API эндпоинты

- [ ] `POST /task` — прием задачи от Worker
  - Input: `{task_id: str, prompt: str, session_data: Optional[dict]}`
  - Output: `{status: "processing", task_id: str}`
- [ ] `GET /task/{task_id}/status` — получение статуса задачи
- [ ] `GET /task/{task_id}/logs` — получение всех логов задачи
- [ ] `POST /task/{task_id}/cancel` — отмена выполнения задачи
- [ ] `GET /health` — healthcheck эндпоинт

#### 6.9 Тестирование

- [ ] Unit тесты для каждого агента
- [ ] Интеграционные тесты с моковыми MCP-серверами
- [ ] E2E тесты полного цикла обработки задачи
- [ ] Тесты потоковой передачи данных через WebSocket
- [ ] Нагрузочное тестирование (локал 100+ параллельных задач)

#### 6.11 Интеграция с Gateway

- [ ] Согласование формата сообщений между Orchestrator и Gateway
- [ ] Тестирование эндпоинта `/task` с реальным Worker
- [ ] Проверка корректности передачи task_id через цепочку
- [ ] Тестирование стримов от Orchestrator до Frontend

---

### 7. Gateway

#### 7.1 В разработке ...

### 8. Data Storage Service

#### 8.1 В разработке ...

### 9. Frontend

#### 9.1 В разработке ...

---

### 10. Доработка RosMCPServer для передачи изображений через сокеты / стримминг зрения роя (интеграция субагента реалтайм алертинга) - добавляет согласованность рою

#### 10.1 В разработке ...

---

### 11. SmolVLA tools

#### 11.1

### 12. Доработка workspace, разработка VDA5050 адаптер хендлера для создания кастомного action действия для использования VLA в миссиях (интеграция SmolVLA в MissionDispatch+MissionControl через кастомные действия) - добавляет индивидуальную автономность

#### 12.1 В разработке ...

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
  - **Конфигурация**: 2 ноды × Tesla V100 (48 GB VRAM)
  - **Диск**: —
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
