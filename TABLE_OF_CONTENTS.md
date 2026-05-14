# Оглавление магистерской диссертации

**Тема:** Организация кооперативного восприятия сцены в группе автономных агентов на основе обмена визуальной информацией

---

> Обозначения: `[~N с.]` — ориентировочный объём раздела в страницах.
> Нумерация рисунков и таблиц: `Рис. X.Y` / `Табл. X.Y`, где X — номер главы, Y — порядковый номер объекта в главе.

---

## Титульный лист *(не нумеруется)*

## Аннотация на русском языке *(не нумеруется)*

## Аннотация на английском языке *(не нумеруется)*

## Содержание

## Введение `[~4–5 с.]`

- Предметная область и мотивация
- Объект исследования: многоагентная робототехническая система с кооперативным восприятием
- Предмет исследования: методы организации взаимодействия, координации и LLM-планирования в группе автономных агентов
- Методы исследования: системный анализ, прототипирование, симуляционный эксперимент, дистилляция моделей
- Актуальность: рост интереса к fleet management, LLM-driven robotics и cooperative perception в промышленных системах
- Цель и задачи (кратко, со ссылкой на аннотацию)
- Основной результат
- Структура работы

---

## Глава 1. Анализ предметной области и обзор существующих решений `[~25–30 с.]`

### 1.1. Кооперативное визуальное восприятие в многоагентных системах
- Постановка задачи: ограничения одиночного агента, роль обмена информацией
- Уровни кооперации: ранний, промежуточный, поздний fusion
- Ключевые подходы: V2VNet, When2com, Where2comm, V2X-ViT, CoBEVT
- Датасеты и бенчмарки: OPV2V, CoPeD
- Trade-off качество восприятия / стоимость коммуникации

### 1.2. Совместное картографирование и локализация (C-SLAM)
- Проблемы C-SLAM: робастность, коммуникационные затраты, масштабируемость
- Decentralized vs. centralized схемы: Swarm-SLAM
- Роль общей карты в системе управления флотом

### 1.3. Координация флота и стандарты интероперабельности
- Протокол VDA5050: архитектура, MQTT, форматы сообщений
- NVIDIA Mission Control и Mission Dispatch как промышленная реализация
- Open RMF: альтернативный подход к fleet management
- Behavior Trees как исполнимый формат миссий
- Облачная робототехника: FogROS2, Robofleet

### 1.4. Большие языковые модели в робототехнике
- Эволюция применения LLM: от интерфейса к семантическому планировщику
- Парадигма ReAct: reasoning + acting + tool use
- Grounding и affordances: SayCan, ProgPrompt
- Безопасность LLM-планов: SELP, constrained decoding
- LLM для многороботных систем: Swarm-GPT, обзор Li et al. 2025

### 1.5. Foundation Models и Vision-Language-Action модели
- RT-2, VoxPoser, OpenVLA, Open X-Embodiment: тренд на generalist control
- Компактные VLA для бортового инференса: SmolVLA, TinyVLA
- π₀: верхняя граница generalist VLA

### 1.6. Симуляционные среды и цифровые двойники
- NVIDIA Isaac Sim: фотореалистичная симуляция, ROS 2 интеграция
- Orbit (Isaac Lab), Pegasus Simulator
- Sim-to-real разрыв как фундаментальное ограничение
- Эффективный LLM-инференс: PagedAttention / vLLM, Qwen2.5

### 1.7. Выводы и результаты по главе 1
- Позиционирование AgentsSwarm в пространстве рассмотренных направлений
- Обоснование архитектурных решений через анализ литературы
- Открытые проблемы, которые решает данная работа

---

## Глава 2. Проектирование архитектуры системы AgentsSwarm `[~20–25 с.]`

### 2.1. Требования к системе
- Функциональные требования: управление флотом на естественном языке, кооперативное восприятие, масштабируемость
- Нефункциональные требования: воспроизводимость, Docker-развёртывание, стандарты интероперабельности
- Ограничения: облачная инфраструктура, доступное оборудование (Selectel, MTS Cloud)

### 2.2. Общая микросервисная архитектура
- Декомпозиция на 8 компонентов: Interface, Orchestrator, vLLM Service, Mission Control, Mission Dispatch, Isaac Sim, ROS 2 Workspace, SmolVLA Tools
- Схема взаимодействия компонентов (Рис. 2.1)
- Разделение слоёв: восприятие / планирование / исполнение миссий

### 2.3. Протокол взаимодействия агентов: Model Context Protocol
- Архитектура MCP: клиент, сервер, транспорт (SSE / stdio)
- Роль MCP в разделении агентского слоя и исполнительного контура
- Три MCP-сервера и их зоны ответственности (Рис. 2.2)

### 2.4. Протокол управления флотом: VDA5050
- Структура сообщений: order, state, connection
- MQTT-брокер (Mosquitto) как шина данных флота
- Маршрут команды: оркестратор → MCP → Mission Control → Mission Dispatch → VDA5050 клиент → робот (Рис. 2.3)

### 2.5. Агентная архитектура оркестратора
- Иерархия агентов: Router → MissionPlanner → специализированные агенты (Рис. 2.4)
- Классификация запросов: 8 категорий, детерминированные правила приоритетов
- Двухфазный MissionPlanner: построение плана / исполнение шагов
- MapAnalyst: vision-LLM для анализа карты сцены

### 2.6. Событийно-ориентированная потоковая модель
- Redis Stream как шина событий интерфейса
- WebSocket как канал событий оркестратора
- Жизненный цикл задачи: pending → running → completed / canceled (Рис. 2.5)

### 2.7. Инфраструктура развёртывания
- Распределение нагрузки по трём машинам (Табл. 2.1)
- Docker Compose стеки для каждого компонента
- Сетевая топология и адресация сервисов

### 2.8. Выводы и результаты по главе 2
- Обоснование архитектурных решений
- Сравнение с аналогами (OpenRMF, коммерческие fleet managers)
- Новизна: интеграция MCP-протокола в VDA5050-контур

---

## Глава 3. Реализация компонентов системы `[~35–40 с.]`

### 3.1. Симуляционная среда: NVIDIA Isaac Sim и ROS 2 Workspace
- Настройка сцены Carter Warehouse: Action Graph, namespaces для нескольких роботов
- Docker Compose для headless-режима с Web Viewer
- ROS 2 Jazzy workspace: сборка, DDS bridge, rosbridge WebSocket (Рис. 3.1)
- Запуск `isaac_ros_mission_client` (VDA5050) для нескольких роботов
- Генерация occupancy map и waypoint graph (Рис. 3.2)

### 3.2. Mission Control: форк NVIDIA и авторские доработки
- Анализ исходного кода NVIDIA Mission Control
- Исправление endpoint `push_map` → `map/update_robot`, `map/metadata`
- Исправление импортов Pydantic в `waypoint_selection_ui`
- Стабилизация Docker-стека: cuOpt, Mosquitto, PostgreSQL (Табл. 3.1)
- Верификация: построение BT и выполнение миссии в симуляторе

### 3.3. Mission Dispatch: форк NVIDIA и авторские доработки
- Исправление legacy endpoint в `packages/controllers/server`
- Исправление конфигурации хоста
- Сквозная проверка: Isaac Sim → VDA5050 → Dispatch → Control → робот

### 3.4. MCP-серверы: глубокая переработка официальных реализаций
- mission-control-mcp: реализация заглушечных endpoints, переход на async tools
- mission-dispatch-mcp: аналогичные доработки, исправление совместимости
- ros-msp: инструменты для ROS 2 топиков через rosbridge WebSocket
- Динамический выбор транспорта stdio / SSE через env vars (Рис. 3.3)
- Инвентарь инструментов по каждому серверу (Табл. 3.2)

### 3.5. vLLM Service: авторский сервис инференса
- Архитектура Data Parallel: координатор (rank 0) + воркер (rank 1), RPC :13345 (Рис. 3.4)
- OpenAI-compatible API endpoint: единая точка входа для клиентов
- Конфигурация `.env.node0` / `.env.node1`, управление `VLLM_GPU_MEMORY_UTILIZATION`
- Скрипты развёртывания `deploy.sh` / `deploy.bat`
- Верификация: smoke-тесты, проверка Data Parallel режима

### 3.6. Orchestrator: главный интеллектуальный микросервис
- Структура FastAPI-приложения: `app.py`, lifespan, dependency injection (Рис. 3.5)
- Агентная архитектура (детально):
  - Router Agent: классификация в 8 категорий (Табл. 3.3)
  - MissionPlanner: двухфазный алгоритм, контракты шагов
  - MapAnalyst: получение PNG-карты, overlay, vision-LLM
  - Navigation / Charging / Patrol / Inspection / FleetOps / SwarmCoordinator / General
- Интеграция с OpenAI Agents SDK: `Runner.run_streamed`, handoff, guardrails
- StreamCollector: seq-нумерация, буферизация, WebSocket `/ws/task/{id}` (Рис. 3.6)
- SessionManager: Redis, история диалога, кэш MCP-результатов
- Retry с backoff, graceful shutdown
- API эндпоинты: сводная таблица (Табл. 3.4)

### 3.7. Interface: веб-платформа управления
- Архитектура: React + FastAPI + Celery + RabbitMQ + Redis Stream (Рис. 3.7)
- Backend: clean architecture, domain / application / infrastructure слои
- Специализированные агенты: General, WebSearch, DeepResearch, ImageGen, PptxGen, AudioTranscribe, SwarmOrchestrator
- Frontend: страницы Chat, TracePanel, Files, Profile; стриминг через WebSocket
- SwarmOrchestratorAgent: проксирование запросов в Orchestrator

### 3.8. Выводы и результаты по главе 3
- Реализованные компоненты: сводная таблица версий и объёма (Табл. 3.5)
- Ключевые технические решения и их обоснование
- 43/43 интеграционных теста API оркестратора

---

## Глава 4. Оптимизация модели SmolVLA для бортового инференса `[~15–20 с.]`

### 4.1. Постановка задачи и мотивация
- Ограничения облачного LLM: задержка, зависимость от сети, стоимость
- Концепция индивидуальной бортовой автономности: SmolVLA как VDA5050 action
- Целевая платформа: NVIDIA Jetson Orin Nano

### 4.2. Архитектура SmolVLA и исходные характеристики
- Teacher-модель: SmolVLA Base (HuggingFace / LeRobot)
- Валидация Teacher на `lerobot/libero`: MSE 0.1782, R² 0.8412 (Табл. 4.1)
- Параметры базовой модели, требования к памяти (6 ГБ VRAM, FP32)

### 4.3. Пайплайн оптимизации
- Stage 1 — Knowledge Distillation: Student-модель с `student_ratio`, функция потерь MSE + KL + attention transfer, 10 эпох, T=3.0, α=0.7 (Рис. 4.1)
- Stage 2 — Mixed Precision Inference (FP16): `torch.cuda.amp`
- Stage 3 — Structured Pruning: 30% весов в Linear-слоях
- Stage 4 — Quantization Analysis (INT8): выявление критических слоёв (Рис. 4.2)

### 4.4. Результаты экспериментов
- Сжатие модели: 443× по параметрам, 12× по VRAM (6 ГБ → <0.5 ГБ) (Табл. 4.2)
- Качество: MSE +9.1%, MAE +5.1%, R² −1.8% — сохранение >90% точности
- Per-action MAE по 7 действиям манипулятора (Табл. 4.3, Рис. 4.3)
- Профилирование инференса: 450 мс → 18 мс (25×) на RTX 4090 (Рис. 4.4)
- Экспорт в ONNX, проверка совместимости с NVIDIA TensorRT

### 4.5. Выводы и результаты по главе 4
- Достижимость бортового инференса на Jetson Orin Nano
- Ограничения: эксперимент в среде `lerobot/libero`, нет верификации на физическом роботе
- Направление развития: кастомный VDA5050 action-handler в Mission Control

---

## Глава 5. Верификация и анализ системы `[~15–20 с.]`

### 5.1. Стратегия тестирования
- Уровни тестирования: unit, контрактные, интеграционные, сквозные (E2E) (Рис. 5.1)
- Инструменты: pytest, Jest, Docker-окружение

### 5.2. Тестирование оркестратора
- Unit-тесты базовых сервисов: health, sessions, streaming, retry
- Контрактные тесты планировщика: шаги, target_robots, зависимости
- Тесты guardrails: валидация вход/выход, категории роутера, silent fallback
- Интеграционные тесты HTTP API: 43/43 ✅ (Табл. 5.1)

### 5.3. Сквозной сценарий: от запроса до выполнения миссии
- Тестовый сценарий: «Отправь робота Carter_1 на координаты (x, y)» (Рис. 5.2)
- Трассировка: Interface → Orchestrator → Navigation Agent → MCP → Mission Control → Mission Dispatch → VDA5050 клиент → Isaac Sim
- Наблюдаемые события в StreamCollector и WebSocket (Рис. 5.3)

### 5.4. Сценарий координации роя
- Тестовый сценарий: SwarmCoordinator для двух роботов с параллельными миссиями
- Распределение задач: поиск свободных роботов, health-check, параллельная отправка
- Мониторинг статусов: polling до COMPLETED/FAILED (Рис. 5.4)

### 5.5. Анализ производительности и ограничений
- Задержка полного контура: от запроса пользователя до старта миссии (Табл. 5.2)
- Узкие места: LLM reasoning latency, MCP round-trip, MQTT delivery
- Ограничения LLM-слоя: риски hallucination, отсутствие формальной верификации
- Централизация vs. отказоустойчивость: анализ single point of failure

### 5.6. Выводы и результаты по главе 5
- Подтверждение работоспособности сквозного контура в симуляции
- Количественные результаты тестирования
- Выявленные ограничения и направления устранения

---

## Заключение `[~3–4 с.]`

- Краткий обзор решённых задач и полученных результатов
- Степень достижения цели
- Научная и практическая значимость
- Перспективы развития:
  - Интеграция SmolVLA как VDA5050 action → бортовая автономность
  - Частичная децентрализация оркестрации (resilience)
  - Формальная верификация LLM-планов (constraint checking, LTL)
  - Перенос на физический флот AMR: sim-to-real валидация
  - Расширение кооперативного восприятия: feature-level fusion между роботами

---

## Библиографический список `[~4–5 с.]`

*Оформление по ГОСТ Р 7.0.5-2008. Все 37 источников из* [REVIEW.md](./REVIEW.md).

Пронумерованный список, порядок — по первому упоминанию в тексте:

1. Han Y. et al. Collaborative Perception in Autonomous Driving... // IEEE ITS Magazine. 2023.
2. Liu S. et al. Towards Vehicle-to-Everything Autonomous Driving... // arXiv. 2023.
3. Wang T.-H. et al. V2VNet... // ECCV. 2020.
4. Liu Y.-C. et al. When2com... // CVPR. 2020.
5. Hu Y. et al. Where2comm... // NeurIPS. 2022.
6. Xu R. et al. V2X-ViT... // ECCV. 2022.
7. Xu R. et al. OPV2V... // ICRA. 2022.
8. Xu R. et al. CoBEVT... // CoRL. 2022.
9. Zhou Y. et al. CoPeD... // RA-L. 2024.
10. Lajoie P.-Y. et al. Towards Collaborative SLAM... // Field Robotics. 2022.
11. Lajoie P.-Y., Beltrame G. Swarm-SLAM... // RA-L. 2024.
12. VDA/VDMA. VDA 5050 v2.0. 2022.
13. van Duijkeren N. et al. An Industrial Perspective... // arXiv. 2023.
14. Open Robotics. Open RMF. 2021–2024.
15. Iovino M. et al. A Survey of Behavior Trees... // RAS. 2022.
16. Chen K. et al. FogROS2... // ICRA. 2023.
17. Sikand K. S. et al. Robofleet... // IROS. 2021.
18. Zeng F. et al. Large Language Models for Robotics: A Survey // arXiv. 2023.
19. Li P. et al. Large Language Models for Multi-Robot Systems // arXiv. 2025.
20. Yao S. et al. ReAct... // ICLR. 2023.
21. Ahn M. et al. SayCan... // CoRL. 2022.
22. Singh I. et al. ProgPrompt... // ICRA. 2023.
23. Pan J. et al. SELP... // ICRA. 2025.
24. Jiao Y.-C. et al. Swarm-GPT... // arXiv. 2023.
25. Brohan A. et al. RT-2... // CoRL. 2023.
26. Huang W. et al. VoxPoser... // CoRL. 2023.
27. Kim M. J. et al. OpenVLA... // CoRL. 2024.
28. OXE Collaboration. Open X-Embodiment... // CoRL. 2023.
29. Black K. et al. π₀... // arXiv. 2024.
30. HuggingFace / LeRobot. SmolVLA... // arXiv. 2025.
31. Wen J. et al. TinyVLA... // RA-L. 2025.
32. NVIDIA Corporation. Isaac Sim Multi-Robot Navigation Tutorial. 2024.
33. Mittal M. et al. Orbit... // RA-L. 2023.
34. Jacinto M. F. et al. Pegasus Simulator... // ICUAS. 2024.
35. Fuller A. et al. A Survey on AI-Driven Digital Twins... // Sensors. 2021.
36. Kwon W. et al. Efficient Memory Management... vLLM // SOSP. 2023.
37. Qwen Team. Qwen2.5 Technical Report // arXiv. 2024.

---

## Приложения

### Приложение А. Глоссарий предметной области

| Термин | Определение |
|--------|-------------|
| AGV / AMR | Automated Guided Vehicle / Autonomous Mobile Robot — категории мобильных промышленных роботов |
| Behavior Tree (BT) | Дерево поведения — иерархическая модульная структура управления логикой задач робота |
| C-SLAM | Collaborative Simultaneous Localization and Mapping — совместная локализация и картографирование несколькими роботами |
| Cooperative Perception | Кооперативное восприятие — обмен перцептивными данными/признаками между агентами для улучшения общего наблюдения сцены |
| Fleet Management | Управление флотом — централизованная диспетчеризация группы роботов |
| Foundation Model | Базовая модель — крупная модель, обученная на широком корпусе данных и адаптируемая для множества задач |
| LLM | Large Language Model — большая языковая модель |
| MCP | Model Context Protocol — открытый протокол взаимодействия LLM-агентов с внешними инструментами и данными |
| MCP-сервер | Сервер, предоставляющий инструменты (tools) агенту через MCP |
| Mission | Миссия — структурированное задание для робота или группы роботов |
| Occupancy Map | Карта занятости — сетка, описывающая проходимость пространства |
| Orchestrator | Оркестратор — центральный сервис, координирующий агентов и исполнение задач |
| ROS 2 | Robot Operating System 2 — фреймворк для разработки роботизированных систем |
| Sim-to-Real | Перенос модели или политики из симуляции на физический робот |
| VDA5050 | Открытый стандарт коммуникации между AGV/AMR и fleet manager |
| VLA | Vision-Language-Action model — мультимодальная модель, генерирующая действия робота из визуального и языкового ввода |
| vLLM | Библиотека для эффективного инференса LLM с алгоритмом PagedAttention |
| Waypoint Graph | Граф путевых точек — граф навигационных узлов на карте |
| WebSocket | Протокол двунаправленной связи для потоковой передачи данных в реальном времени |

### Приложение Б. Список сокращений

| Сокращение | Расшифровка |
|-----------|-------------|
| AGV | Automated Guided Vehicle |
| AMR | Autonomous Mobile Robot |
| API | Application Programming Interface |
| BT | Behavior Tree |
| C-SLAM | Collaborative Simultaneous Localization and Mapping |
| DDS | Data Distribution Service |
| E2E | End-to-End |
| FSM | Finite State Machine |
| GPU | Graphics Processing Unit |
| IMU | Inertial Measurement Unit |
| LiDAR | Light Detection and Ranging |
| LLM | Large Language Model |
| MAE | Mean Absolute Error |
| MCP | Model Context Protocol |
| MPC | Model Predictive Control |
| MSE | Mean Squared Error |
| MQTT | Message Queuing Telemetry Transport |
| ROS | Robot Operating System |
| SDK | Software Development Kit |
| SSE | Server-Sent Events |
| V2V | Vehicle-to-Vehicle |
| V2X | Vehicle-to-Everything |
| VDA | Verband der Automobilindustrie |
| VLA | Vision-Language-Action |
| VRAM | Video Random Access Memory |

### Приложение В. Технические характеристики вычислительной инфраструктуры

| Машина | Провайдер | Конфигурация | Назначение |
|--------|-----------|--------------|------------|
| Симуляция | Selectel | 4 vCPU, 16 ГБ RAM, RTX 4090 (24 ГБ VRAM), 128 ГБ SSD, Ubuntu 24.04 | Isaac Sim + ROS 2 workspace + Mission Control/Dispatch |
| Микросервисы | Selectel | 4 vCPU, 8 ГБ RAM, 128 ГБ SSD, Ubuntu 24.04 | Interface + Orchestrator + Redis + RabbitMQ + MinIO + PostgreSQL |
| LLM-кластер | MTS Cloud | 2 ноды × Tesla V100-PCIE (32 ГБ VRAM), 1.6 ТБ/нода, Ubuntu 24.04 | vLLM Data Parallel (Qwen2.5-Instruct) |

### Приложение Г. Ключевые фрагменты кода

- Г.1. Конфигурация агентов оркестратора: `router.py`, `prompts.py`
- Г.2. Реализация MissionPlanner: двухфазный алгоритм (`planner.py`)
- Г.3. StreamCollector: seq-нумерация и WebSocket push (`streaming.py`, `websocket_stream.py`)
- Г.4. Конфигурация MCP-серверов: динамический выбор транспорта (`mcp.py`)
- Г.5. Пайплайн дистилляции SmolVLA: функция потерь и training loop

### Приложение Д. Протоколы экспериментов

- Д.1. Протокол тестирования API оркестратора (43 теста): входные данные, ожидаемые и фактические результаты
- Д.2. Протокол эксперимента по дистилляции SmolVLA: гиперпараметры, метрики по эпохам
- Д.3. Протокол профилирования инференса: условия измерения, результаты latency
