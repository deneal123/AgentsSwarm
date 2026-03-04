# ROS2 Bridge

## Цель

ROS2 Bridge обеспечивает двунаправленный обмен данными между локальной ROS 2-экосистемой робота и облачными сервисами (Gateway, Orchestrator). Он транслирует ROS 2 топики в MQTT/gRPC и обратно, а также предоставляет WebSocket-интерфейс визуализации через Foxglove Bridge.

---

## Платформа и базовый образ

ROS2 Bridge работает на **ROS 2 Jazzy** (LTS, май 2024). Docker-контейнер строится на базе:

- **Разработка**: `osrf/ros:jazzy-desktop-full` — полный набор (RViz2, rqt, Foxglove Bridge, GUI-инструменты)
- **Production**: `osrf/ros:jazzy-ros-base` — минимальный набор (только runtime, без GUI)

Контейнер включает следующие ROS 2 пакеты:

| Пакет | Назначение |
|-------|-----------|
| ros-jazzy-foxglove-bridge | WebSocket-мост для браузерной визуализации ROS 2 данных |
| ros-jazzy-rqt* | Набор GUI-инструментов для отладки (графики, логи, топики) |
| ros-jazzy-rviz2 | 3D-визуализация робота и данных сенсоров |
| ros-jazzy-teleop-twist-keyboard | Ручное управление роботом через клавиатуру |
| ros-jazzy-tf2-tools | Работа с деревом систем координат (TF) |

Python-зависимости: numpy, matplotlib, opencv — необходимы для обработки сенсорных данных и предварительной фильтрации на уровне Bridge.

---

## Основные функции

- Подписка/публикация ROS 2 топиков (sensor_msgs, nav_msgs, geometry_msgs)
- Трансформация сообщений в Protobuf/JSON для передачи по MQTT/gRPC
- Управление QoS-профилями ROS 2 при потере связи
- Агрегация и фильтрация данных на уровне Bridge (не отправлять лишние кадры)
- WebSocket-визуализация через Foxglove Bridge (порт 8765)
- Буферизация и backpressure при медленной сети

---

## Архитектура Bridge-контейнера

### Внутренние ROS 2 узлы

Контейнер ros2-bridge содержит несколько ROS 2 узлов, организованных как ament_python пакеты:

| Узел | Назначение |
|------|-----------|
| topic_translator | Подписка на ROS 2 топики робота и публикация в MQTT (через paho-mqtt) |
| command_receiver | Подписка на MQTT-команды от Orchestrator и публикация в ROS 2 топики (/cmd_vel, /joint_trajectory) |
| data_aggregator | Агрегация и фильтрация данных перед отправкой (сэмплирование, сжатие, event-detection) |
| health_reporter | Формирование и отправка статуса робота по MQTT |
| image_forwarder | Передача сжатых изображений: формирование ссылок на MinIO вместо inline-передачи |

### Структура ROS 2 Workspace

Все Bridge-узлы разрабатываются как ament_python пакеты в едином workspace:

```
ros2_ws/
├── src/
│   ├── agentswarm_bridge/           # Основной пакет трансляции
│   │   ├── agentswarm_bridge/
│   │   │   ├── __init__.py
│   │   │   ├── topic_translator.py
│   │   │   ├── command_receiver.py
│   │   │   ├── data_aggregator.py
│   │   │   └── health_reporter.py
│   │   ├── package.xml
│   │   ├── setup.py
│   │   └── setup.cfg
│   └── agentswarm_msgs/             # Кастомные типы сообщений
│       ├── msg/
│       │   ├── RobotStatus.msg
│       │   └── TaskCommand.msg
│       └── package.xml
├── build/
├── install/
└── log/
```

### Система сборки

Сборка осуществляется через **colcon** (Collective Construction):

- `colcon build` — полная сборка workspace
- `colcon build --packages-select agentswarm_bridge` — сборка одного пакета
- `colcon build --symlink-install` — symbolic links для Python (изменения видны без пересборки)
- `source install/setup.bash` — активация собранных пакетов

Зависимости пакета определяются в `package.xml` (формат 3) и управляются через `rosdep`.

---

## Маппинг ROS 2 топиков на MQTT

### Edge → Cloud (телеметрия и сенсоры)

| ROS 2 топик | Тип сообщения | MQTT-топик | QoS | Частота |
|-------------|--------------|------------|-----|---------|
| /camera/image_raw | sensor_msgs/Image | agentswarm/{tenant}/{robot_id}/camera/image_meta | 0 | 1–5 FPS (сэмплирование) |
| /camera/image_compressed | sensor_msgs/CompressedImage | → MinIO upload + ссылка в MQTT | 1 | По событию |
| /scan | sensor_msgs/LaserScan | agentswarm/{tenant}/{robot_id}/lidar/scan | 0 | 5–10 Hz |
| /odom | nav_msgs/Odometry | agentswarm/{tenant}/{robot_id}/telemetry/odom | 1 | 5 Hz |
| /imu/data | sensor_msgs/Imu | agentswarm/{tenant}/{robot_id}/telemetry/imu | 0 | 10 Hz |
| /joint_states | sensor_msgs/JointState | agentswarm/{tenant}/{robot_id}/telemetry/joints | 0 | 5 Hz |
| /robot_status | custom_msgs/RobotStatus | agentswarm/{tenant}/{robot_id}/status | 1 (retained) | 1 Hz |
| /tf | tf2_msgs/TFMessage | agentswarm/{tenant}/{robot_id}/telemetry/tf | 0 | 10 Hz |

### Cloud → Edge (команды)

| MQTT-топик | ROS 2 топик | Тип сообщения | QoS | Описание |
|-----------|-------------|--------------|-----|----------|
| agentswarm/{tenant}/{robot_id}/cmd/velocity | /cmd_vel | geometry_msgs/Twist | 2 | Команда движения |
| agentswarm/{tenant}/{robot_id}/cmd/trajectory | /joint_trajectory | trajectory_msgs/JointTrajectory | 2 | Команда для манипулятора |
| agentswarm/{tenant}/{robot_id}/cmd/navigate | /navigate_to_pose | geometry_msgs/PoseStamped | 2 | Навигация к точке |
| agentswarm/{tenant}/{robot_id}/cmd/stop | /emergency_stop | std_msgs/Bool | 2 | Экстренная остановка |
| agentswarm/{tenant}/{robot_id}/model/update | — (обрабатывается Edge AI Proxy) | — | 2 | Команда обновления модели |

---

## Foxglove Bridge — WebSocket-визуализация

### Назначение

Foxglove Bridge (ros-jazzy-foxglove-bridge) предоставляет WebSocket-интерфейс (порт 8765) для подключения внешних клиентов визуализации к ROS 2 данным робота.

### Архитектура подключения

Foxglove Bridge поддерживает три режима интеграции с Frontend AgentsSwarm:

| Режим | Путь данных | Применение |
|-------|-----------|-----------|
| Прямой | Frontend → ws://robot_ip:8765 | Разработка, 1–3 робота |
| Через Gateway | Frontend → Gateway WS → агрегация → Foxglove Bridge каждого робота | Production, масштабирование |
| Через MQTT | Foxglove Bridge → topic_translator → MQTT → Gateway → Frontend | Production, единый канал |

### Доступные данные через Foxglove

- Позиция и ориентация робота (/odom, /tf)
- Облако точек LiDAR (/scan)
- Изображения камеры (/camera/image_compressed)
- Карта окружения (/map)
- Маркеры визуализации (/visualization_markers)
- Дерево систем координат (TF tree)

### Подключение через Foxglove Studio Web

1. На роботе (или в dev-контейнере): Foxglove Bridge запускается автоматически на порту 8765
2. Оператор открывает Foxglove Studio Web (https://studio.foxglove.dev/)
3. Подключается к ws://robot_ip:8765
4. Получает доступ ко всем ROS 2 топикам в реальном времени

---

## Агрегация и фильтрация данных

### Стратегии снижения нагрузки на канал

Узел data_aggregator реализует следующие стратегии:

| Стратегия | Описание | Применение |
|-----------|----------|-----------|
| Temporal sampling | Пропуск кадров: каждый N-й кадр камеры | Камера (30 FPS → 1–5 FPS) |
| Event-driven | Отправка только при значительном изменении | Одометрия (если робот стоит — не отправлять) |
| Compression | Сжатие изображений (JPEG quality 60–80%) | Камера, перед загрузкой в MinIO |
| Metadata-only | Отправка только метаданных (размеры, timestamp), тело — в MinIO | Большие payload (изображения, облака точек) |
| Priority-based | При слабой связи — только высокоприоритетные данные | Все топики (safety > telemetry > vision) |

### Backpressure

При перегрузке сети или медленном MQTT-соединении Bridge:

- Буферизует сообщения в локальной очереди (ограниченный размер)
- Низкоприоритетные сообщения отбрасываются первыми
- Критические сообщения (safety, emergency) — никогда не отбрасываются
- При восстановлении связи — отправка буферизованных данных в порядке приоритета

---

## QoS-профили ROS 2

### Настройка QoS под условия Edge

| Профиль | Reliability | Durability | History | Depth | Применение |
|---------|-----------|-----------|---------|-------|-----------|
| Sensor | Best Effort | Volatile | Keep Last | 5 | Камера, LiDAR, IMU |
| Reliable | Reliable | Transient Local | Keep Last | 10 | Команды, статус |
| Bulk | Best Effort | Volatile | Keep Last | 1 | Облако точек, большие данные |

При потере связи с облаком QoS-профили ROS 2 остаются неизменными — локальные узлы продолжают работать. Bridge переключается в режим буферизации для MQTT.

---

## Особенности реализации

### Поддержка ROS 2 Jazzy

Bridge построен на ROS 2 Jazzy — последней LTS-версии. Это обеспечивает:

- Стабильную API-поверхность до 2029 года
- Совместимость с Jazzy-пакетами экосистемы
- Поддержку новых QoS-политик и улучшенного DDS

### Mapping типов

Каждый ROS 2 тип сообщения маппится в соответствующую Protobuf-схему:

- sensor_msgs/Image → agentswarm.proto.SensorImage
- nav_msgs/Odometry → agentswarm.proto.Odometry
- geometry_msgs/Twist → agentswarm.proto.VelocityCommand
- custom_msgs/RobotStatus → agentswarm.proto.RobotStatus

Маппинг определён декларативно и может расширяться без изменения кода Bridge.

### Работа через VS Code Remote Containers

Для разработки Bridge-узлов рекомендуется подключение VS Code к dev-контейнеру:

1. Контейнер запускается с монтированием ros2_ws/src/ как volume
2. VS Code подключается через расширение Remote — Containers
3. Разработчик получает полный IntelliSense для ROS 2 API (rclpy)
4. Изменения в Python-коде видны сразу (при сборке с --symlink-install)
5. Терминал VS Code работает внутри контейнера — доступны ros2 run, ros2 topic echo и все инструменты
