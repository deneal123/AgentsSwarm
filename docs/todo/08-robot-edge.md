# TODO: Robot Edge

Программный стек на бортовом компьютере робота (Jetson). ROS 2, MQTT bridge, Edge AI Proxy, SmolVLA Edge, автономный режим.

---

## Этап 1 — Инициализация проекта

- [x] **Создать репозиторий robot_edge.** Poetry-проект с зависимостями: paho-mqtt, pydantic-settings, prometheus-client, structlog, numpy, opencv-python-headless. ROS 2 зависимости через rosdep.

- [x] **Настроить .pre-commit-config.yaml.** Хуки: ruff, mypy, bandit.

- [x] **Создать Dockerfile.** Базовый образ `osrf/ros:jazzy-desktop-full`, установка JetPack-совместимых пакетов (CUDA, TensorRT, PyTorch для ARM). Entrypoint: ROS 2 launch файл.

- [x] **Создать Dockerfile.vnc.** Расширение основного Dockerfile: добавление TurboVNC + noVNC для удалённой визуализации RViz2 и Foxglove. Порт 6080.

- [x] **Создать docker-compose.edge.yml.** Compose для Edge-стека на Jetson: edge-ai-proxy, ros2-bridge, foxglove-bridge, smolvla-edge. Shared network, GPU runtime.

- [x] **Создать config.py.** Pydantic Settings: ROBOT_ID, ROBOT_MODEL, MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, CLOUD_TRITON_URL, CLOUD_VLLM_URL, CLOUD_SMOLVLA_URL, EDGE_MODE (online/offline/hybrid), LOG_LEVEL.

---

## Этап 2 — ROS 2 Bridge

- [x] **ROS2-MQTT bridge node (bridge/ros2_mqtt_bridge.py).** ROS 2 node, подписанный на локальные топики (cmd_vel, joint_states, camera/image_raw, scan), публикующий в MQTT. Обратное направление: MQTT commands → ROS 2 topics.

- [x] **Topic mapper (bridge/topic_mapper.py).** Конфигурируемый маппинг: ROS 2 topic → MQTT topic. Пример: `/robot/odom` → `telemetry/{robot_id}/odom`, `commands/{robot_id}/move` → `/robot/cmd_vel`. Загрузка из YAML-конфига.

- [x] **Serializer (bridge/serializer.py).** Конвертация ROS 2 messages в JSON для MQTT и обратно. Поддержка типов: geometry_msgs/Twist, sensor_msgs/Image (сжатие JPEG), sensor_msgs/LaserScan, nav_msgs/Odometry.

- [x] **Image compression.** Сжатие camera frames перед отправкой в MQTT: JPEG quality 80% для телеметрии, quality 95% для inference-запросов. Configurable.

- [x] **Throttling.** Rate limiting для телеметрии: odometry 10 Hz → MQTT 2 Hz, camera 30 FPS → MQTT 1 FPS (для облака), LiDAR 10 Hz → MQTT 1 Hz. Configurable per-topic.

- [x] **Foxglove Bridge.** Запуск foxglove_bridge node на порту 8765 для WebSocket-доступа к ROS 2 данным. Используется для удалённой визуализации через Foxglove Studio.

---

## Этап 3 — Edge AI Proxy

- [x] **Proxy router (ai_proxy/proxy.py).** Маршрутизатор inference-запросов: определяет — выполнить локально (edge model) или отправить в облако (cloud model). Решение на основе: тип задачи, latency requirements, connectivity status.

- [x] **Model manager (ai_proxy/model_manager.py).** Загрузка моделей из MinIO при старте и по команде обновления. Хранение локально в `/models/`. Проверка checksum. Атомарная замена (download → verify → swap).

- [x] **Fallback logic (ai_proxy/fallback.py).** Стратегии: cloud_preferred (облако, при неудаче — edge), edge_preferred (edge, при неудаче — облако), edge_only (только локально, для offline), cloud_only (только облако, для тяжёлых задач).

- [x] **Local cache (ai_proxy/cache.py).** LRU-кэш результатов inference: если одинаковая сцена (hash image) уже обработана < 1 секунды назад — вернуть кэшированный результат. Для снижения нагрузки на GPU.

- [x] **Connection monitor.** Периодическая проверка связи с облаком (MQTT ping + gRPC health check). При потере связи — автоматическое переключение на edge_only. При восстановлении — возврат к cloud_preferred.

---

## Этап 4 — SmolVLA Edge

- [x] **Model loader (smolvla_edge/inference.py).** Загрузка оптимизированной SmolVLA Edge (~150M params) в формате ONNX или TensorRT. Целевая латентность: <100ms на Jetson Orin NX.

- [x] **TensorRT оптимизация.** Конвертация SmolVLA ONNX → TensorRT engine для Jetson (FP16). Benchmark latency: ONNX runtime vs TensorRT.

- [x] **Action executor (smolvla_edge/action_executor.py).** Исполнение action chunks: получение chunk от SmolVLA → публикация действий в ROS 2 топик cmd_vel / joint_trajectory с заданной частотой (20 Hz).

- [x] **Continuous control loop.** Цикл: capture image → SmolVLA inference → execute actions → capture next → prefetch next chunk. Overlap inference и execution для минимизации задержки.

- [x] **Safety constraints.** Ограничения на action output: max velocity, max acceleration, workspace boundaries, joint limits. Clipping actions перед выполнением.

---

## Этап 5 — Автономный режим

- [ ] **Offline mode (autonomy/offline_mode.py).** Переключение при потере MQTT-соединения (LWT timeout). Логика: продолжить текущую задачу, switch to edge_only inference, буферизировать telemetry и events.

- [ ] **Safety monitor (autonomy/safety_monitor.py).** Watchdog: проверка heartbeat всех подсистем (ROS 2, MQTT, AI Proxy, sensors). При сбое — emergency stop. Ограничение скорости при низком заряде батареи.

- [ ] **Emergency stop.** Немедленная остановка робота при: obstacle < safety_distance, sensor failure, watchdog timeout, explicit cloud command. Публикация zero-velocity в cmd_vel + event в MQTT (при наличии связи).

- [ ] **Telemetry buffer (autonomy/buffer.py).** Circular buffer для телеметрии и событий при offline. Max size: 10MB. При восстановлении связи — поэтапная выгрузка буфера в MQTT с backpressure.

- [ ] **State sync (autonomy/sync.py).** Синхронизация при восстановлении связи: отправка accumulated telemetry, текущего состояния, accumulated events. Приём пропущенных команд и обновлений конфигурации.

- [ ] **Battery management.** Мониторинг заряда: при < 20% — уведомление облака, при < 10% — завершение текущей задачи и возврат на базу, при < 5% — emergency park и shutdown.

---

## Этап 6 — ROS 2 Nodes

- [ ] **Telemetry node (ros2/nodes/telemetry_node.py).** ROS 2 node: подписка на odom, battery_state, imu, joint_states. Агрегация в единое сообщение RobotTelemetry. Publish с настраиваемой частотой.

- [ ] **Command node (ros2/nodes/command_node.py).** ROS 2 node: приём команд из MQTT bridge, конвертация в ROS 2 actions (MoveBase, FollowJointTrajectory). Мониторинг выполнения action, публикация ack/result.

- [ ] **Sensor node (ros2/nodes/sensor_node.py).** ROS 2 node: управление камерами (V4L2/CSI), LiDAR, IMU. Публикация raw data в ROS 2 topics. Diagnostics при sensor failure.

- [ ] **Launch файл (ros2/launch/edge_launch.py).** ROS 2 launch: запуск всех нод (telemetry, command, sensor, bridge, foxglove) с параметрами из config.yaml. Respawn при crash.

---

## Этап 7 — Тесты

- [x] **conftest.py.** Фикстуры: mock ROS 2 (rclpy test utilities), mock MQTT broker, sample ROS 2 messages (Odometry, Image, LaserScan), mock SmolVLA model.

- [x] **Unit: topic mapper.** Тесты маппинга ROS 2 ↔ MQTT: известные топики, unknown topic fallback, configurable overrides.

- [x] **Unit: serializer.** Тесты конвертации: Twist ↔ JSON, Image → compressed JPEG, Odometry ↔ JSON. Round-trip integrity.

- [x] **Unit: fallback logic.** Тесты стратегий: cloud_preferred (cloud OK → cloud, cloud fail → edge), edge_only при offline, connection recovery.

- [x] **Unit: safety monitor.** Тесты watchdog: heartbeat OK → no action, heartbeat missing → e-stop, low battery → return to base.

- [x] **Unit: telemetry buffer.** Тесты circular buffer: fill, overflow (drop oldest), drain при sync, size limits.

- [x] **Integration: bridge.** Тест ROS 2 topic → MQTT publish → MQTT subscribe (full loop). Requires ROS 2 test environment.

- [x] **Integration: edge AI proxy.** Тест: inference request → route to mock cloud/edge → result. Fallback при mock cloud failure.
