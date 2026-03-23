# TODO: 06_mission_dispatch_mcp_integration

## Описание
Интеграция системы назначения миссий `isaac_mission_dispatch` по стандарту VDA5050, включение ее в `ros_msp_service` (MCP сервер) и создание LLM-оркестратора на основе OpenAI Agents.

## Задачи
- [ ] **Настройка MQTT Брокера**
  - Установить `mosquitto` (`sudo apt install mosquitto mosquitto-clients`).
  - Запустить брокер: `sudo systemctl start mosquitto`.
- [ ] **Настройка и запуск Mission Client (VDA5050)**
  - Клонировать/Скомпилировать пакет `isaac_ros_vda5050_client_bringup` для Isaac ROS Workspace.
  - Добавить в `launch`-сценарий запуск узлов клиентов.
  - В цикле по роботам создать `Node(package='isaac_ros_vda5050_client_bringup', executable='isaac_ros_vda5050_client.launch.py', ...)`
  - Передать корректные аргументы: `namespace:={robot}`, `serial_number:={robot}`, `mqtt_host_name:="localhost"`.
- [ ] **Запуск сервера Mission Dispatch Server**
  - Поднять сервер (FastAPI/базовая имплементация из `isaac_mission_dispatch`).
  - Проверить его доступность по `http://<IP>:5000` и изучить swagger/OpenAPI эндпоинты для POST запросов `/api/v1/missions`.
- [ ] **Разработка инструмента MCP в `ros_msp_service`**
  - В репозитории `ros_msp_service/ros_mcp/tools/` создать новый инструмент (например, `mission.py`).
  - Написать асинхронную функцию `send_mission(robot: str, mission_tree: list)`.
  - Задекорировать как `@mcp.tool(description="Send a route/mission via Mission Dispatch REST API")`.
  - Реализовать тело функции с использованием HTTP клиента (например, `aiohttp` или `httpx`), который шлет POST на API сервер Mission Dispatch с заданными параметрами.
- [ ] **Разработка Оркестратора (LLM Агент)**
  - Создать Python-скрипт или папку конфигурации оркестратора `orchestrator/agent.py`.
  - Использовать любой фреймворк (Langchain / OpenAI Swarm / OpenAI Agents SDK).
  - Настроить инструмент `send_mission` в схему агента.
  - Настроить системный промпт: "Ты диспетчер роботов в складской зоне. Если просят отправить робота в точку, используй send_mission с соответствующими координатами в waypoints."
- [ ] **Комплексное Тестирование E2E (End-to-End)**
  - Запуск: Terminal 1 - Isaac Sim (роботы).
  - Terminal 2 - Nav2 + SLAM + Mission Client Launch (ROS 2 `multi_robot_nav2.launch.py`).
  - Terminal 3 - `mosquitto` и Mission Dispatch сервер.
  - Terminal 4 - `ros-mcp --transport=stdio`.
  - Terminal 5 - Запуск Агента-оркестратора.
  - Отправить тестовый промпт: "Отправь carter1 на X=5.0, Y=2.0". Агент должен сгенерировать `mission_tree` и вызвать тул, после чего робот начнёт движение в симуляции.
