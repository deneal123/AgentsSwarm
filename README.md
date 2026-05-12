# workspace_isaac_simulation

`workspace_isaac_simulation` — это ROS 2 workspace для запуска и тестирования Isaac Sim / Isaac ROS окружения с VDA5050 Mission Client.

Проект поднимает контейнеризированную среду ROS 2, в которой уже настроены необходимые зависимости, workspace и клиент для взаимодействия с Mission Dispatch / Mission Control через VDA5050.

Основной сценарий использования:

- инициализация submodules;
- сборка ROS 2 workspace под нужную версию ROS и Ubuntu;
- запуск контейнера с подготовленным окружением;
- вход в контейнер `vda5050_client`;
- запуск и отладка ROS 2-ноды Mission Client для работы с Isaac Sim.

Workspace внутри контейнера расположен по пути:

```text
~/IsaacSim-ros_workspaces/build_ws/jazzy/jazzy_ws

## Первый запуск

Перед первым запуском инициализируйте submodules и соберите ROS 2 workspace:

```bash
make first-start
```

При необходимости версии можно переопределить:

```bash
make first-start ROS_DISTRO=humble UBUNTU_VERSION=22.04
```

## Запуск контейнера

Запустить контейнер в фоне:

```bash
make up
```

## Остановка контейнера

Остановить текущий контейнер:

```bash
make down
```

## Перезапуск контейнера

Остановить старый контейнер и запустить новый:

```bash
make restart
```

## Вход в контейнер

Войти в контейнер с уже настроенным окружением:

```bash
make shell
```

## Дополнительные команды

Показать статус контейнеров:

```bash
make ps
```

Показать логи:

```bash
make logs
```

Остановить контейнер и удалить volumes:

```bash
make clean
```

## Расположение workspace

Workspace внутри контейнера находится по пути:

```text
~/IsaacSim-ros_workspaces/build_ws/jazzy/jazzy_ws
```

Если workspace собирался под другую версию ROS, путь будет соответствовать выбранному `ROS_DISTRO`.

Например для `humble`:

```text
~/IsaacSim-ros_workspaces/build_ws/humble/humble_ws
```

## Важное замечание

Перед запуском навигации убедитесь, что `origin` в конфигурации карты корректно согласован с `origin` сцены в Isaac Sim.

## Запуск нескольких инстансов роботов

При работе с несколькими роботами необходимо запускать отдельный клиент VDA5050 для каждого экземпляра. Для этого используются параметры запуска, позволяющие настроить уникальные идентификаторы и конфигурации для каждого робота.

## Запуск ros2bridge для работы ros-mcp сервера

```bash
# через комманду
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### Базовая команда запуска для одного робота


*Иначе не будет работать, делать при старте*

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0.0 --y 0.0 --z 0.0 \
  --roll 0.0 --pitch 0.0 --yaw 0.0 \
  --frame-id map \
  --child-frame-id odom &

ros2 run tf2_ros static_transform_publisher \
  --x 0.06 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 0.0 \
  --frame-id base_link \
  --child-frame-id front_2d_lidar &

ros2 run tf2_ros static_transform_publisher \
  --x -0.52 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 3.14159 \
  --frame-id base_link \
  --child-frame-id back_2d_lidar &
```

```bash
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  init_pose_x:=0.0 \
  init_pose_y:=0.0 \
  reconnect_period:=30 \
  mqtt_host_name:=185.55.57.82 \
  map:=/workspace/maps/map.yaml \
  nav_params_file:=/workspace/nav2_params/nav2_params_custom.yaml
```

### Команда запуска для нескольких роботов

*Иначе не будет работать, делать при старте*

*Внимательно пересмотреть координаты роботов относительно симуляции в isaac*
```bash
# Публикуем только TF лидаров — через namespace топик
ros2 run tf2_ros static_transform_publisher \
  --x 0.06 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 0.0 \
  --frame-id base_link \
  --child-frame-id front_2d_lidar \
  --ros-args --remap /tf_static:=/carter01/tf_static &

ros2 run tf2_ros static_transform_publisher \
  --x -0.52 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 3.14159 \
  --frame-id base_link \
  --child-frame-id back_2d_lidar \
  --ros-args --remap /tf_static:=/carter01/tf_static &

ros2 run tf2_ros static_transform_publisher \
  --x 0.06 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 0.0 \
  --frame-id base_link \
  --child-frame-id front_2d_lidar \
  --ros-args --remap /tf_static:=/carter02/tf_static &

ros2 run tf2_ros static_transform_publisher \
  --x -0.52 --y 0.0 --z 0.38 \
  --roll 0.0 --pitch 0.0 --yaw 3.14159 \
  --frame-id base_link \
  --child-frame-id back_2d_lidar \
  --ros-args --remap /tf_static:=/carter02/tf_static &
```

*Внимательно пересмотреть координаты роботов относительно симуляции в isaac*
```bash
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  serial_number:=carter01 \
  namespace:=carter01 \
  ros_to_mqtt_name:=Carter01_RosToMqttBridge \
  mqtt_to_ros_name:=Carter01_MqttToRosBridge \
  init_pose_x:=-6.69 \
  init_pose_y:=-9.66 \
  reconnect_period:=30 \
  map:=/workspace/maps/map.yaml \
  nav_params_file:=/workspace/nav2_params/nav2_params_carter01.yaml \
  use_namespace:=true \
  mqtt_host_name:=185.55.57.82 &
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  serial_number:=carter02 \
  namespace:=carter02 \
  ros_to_mqtt_name:=Carter02_RosToMqttBridge \
  mqtt_to_ros_name:=Carter02_MqttToRosBridge \
  init_pose_x:=7.32 \
  init_pose_y:=-9.98 \
  reconnect_period:=30 \
  map:=/workspace/maps/map.yaml \
  nav_params_file:=/workspace/nav2_params/nav2_params_carter02.yaml \
  use_namespace:=true \
  mqtt_host_name:=185.55.57.82 &
```


## Параметры ROS для настройки клиента VDA5050

| ROS Parameter | Type | Default | Description |
|---------------|------|---------|-------------|
| `namespace` | string | (Empty) | Пространство имен ROS для графа. Например: `carter` |
| `mqtt_host_name` | string | `localhost` | IP-адрес MQTT брокера. Например: `192.168.25.32` |
| `mqtt_port` | string | `1883` | Порт MQTT брокера |
| `mqtt_transport` | string | `tcp` | Протокол передачи MQTT (`tcp` или `websockets`) |
| `mqtt_ws_path` | string | `''` | Путь WebSocket при использовании `websockets` |
| `interface_name` | string | `uagv` | Название интерфейса. Формирует сегмент MQTT топика: `<interface_name>/<major_version>/<manufacturer>/<serial_number>/[order\|state\|instantActions]` |
| `major_version` | string | `v2` | Версия VDA5050. Сегмент MQTT топика |
| `manufacturer` | string | `RobotCompany` | Производитель AGV. Сегмент MQTT топика |
| `serial_number` | string | `carter01` | Уникальный серийный номер AGV. Сегмент MQTT топика |
| `robot_type` | string | `amr` | Тип робота (`amr` или `arm`) |
| `ros_publisher_type` | string | `vda5050_msgs/Order` | Тип ROS сообщения для входящих MQTT |
| `ros_subscriber_type` | string | `vda5050_msgs/AGVState` | Тип ROS сообщения для исходящих MQTT |
| `ros_to_mqtt_name` | string | `Carter01_RosToMqttBridge` | Имя MQTT клиента для узла RosToMqtt |
| `mqtt_to_ros_name` | string | `Carter01_MqttToRosBridge` | Имя MQTT клиента для узла MqttToRos |
| `retry_forever` | bool | `true` | Бесконечное переподключение к MQTT брокеру |
| `reconnect_period` | int | `5` | Задержка перед повторным подключением (сек) |
| `num_retries` | int | `10` | Количество попыток подключения (если `retry_forever: false`) |
| `ros_recorder` | bool | `false` | Запуск `isaac_ros_scene_recorder` при `true` |
| `config_file` | string | `vda5050_client_params.yaml` | Путь к файлу параметров VDA5050 клиента |

## Дополнительные параметры навигации

| ROS Parameter | Type | Default | Description |
|---------------|------|---------|-------------|
| `use_namespace` | bool | `false` | Применять пространство имен к навигационному стеку |
| `use_composition` | bool | `false` | Использовать композицию Nav2 bringup |
| `use_sim_time` | bool | `false` | Использовать симуляционное время (Omniverse Isaac Sim) |
| `init_pose_x` | float | `0.0` | Начальная позиция X |
| `init_pose_y` | float | `0.0` | Начальная позиция Y |
| `init_pose_yaw` | float | `0.0` | Начальная ориентация (рыскание) |
| `map` | string | `{path}/carter_warehouse_navigation.yaml` | Путь к файлу карты |
| `nav_params_file` | string | `{path}/carter_navigation_params.yaml` | Путь к файлу параметров навигации |
| `info_generator_params_file` | string | `{path}/json_info_generator_params.yaml` | Путь к файлу параметров JSON Info Generator |
| `launch_rviz` | bool | `false` | Запускать RViz |

## Проверка DDS/ROS окружения в контейнере

После входа в контейнер проверь окружение и доступность топиков до запуска mission-клиентов:

```bash
printenv | egrep "ROS_DOMAIN_ID|RMW_IMPLEMENTATION|ROS_LOCALHOST_ONLY|FASTRTPS_DEFAULT_PROFILES_FILE"
ros2 topic list
ros2 topic echo /clock --once
```

Ожидаемые значения:

- `ROS_DOMAIN_ID` совпадает с Isaac Sim.
- `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`.
- `ROS_LOCALHOST_ONLY=0`.
- `FASTRTPS_DEFAULT_PROFILES_FILE` указывает на существующий XML профиль.

Если `/clock` виден, но odom-топики отсутствуют, проверь namespace и топик одометрии в графе Isaac Sim (`/odom`, `/chassis/odom` или `/<robot_ns>/chassis/odom`) и в параметрах `nav_params_file`.
