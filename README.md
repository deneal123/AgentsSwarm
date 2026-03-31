git submodule update --init --recursive
./build_ros.sh -d jazzy -v 24.04
Workspace будет в: ~/projects/IsaacSim-ros_workspaces/build_ws/jazzy/jazzy_ws




3. Run the mission client (Launch mission client and navigation2):

## Запуск нескольких инстансов роботов

При работе с несколькими роботами необходимо запускать отдельный клиент VDA5050 для каждого экземпляра. Для этого используются параметры запуска, позволяющие настроить уникальные идентификаторы и конфигурации для каждого робота.

### Базовая команда запуска

```bash
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py
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
| `map` | string | `/home/$USER/workspaces/isaac_ros-dev/src/isaac_ros_cloud_control/isaac_ros_vda5050_client_bringup/maps/carter_warehouse_navigation.yaml` | Путь к файлу карты |
| `nav_params_file` | string | `/home/$USER/workspaces/isaac_ros-dev/src/isaac_ros_cloud_control/isaac_ros_vda5050_client_bringup/config/carter_navigation_params.yaml` | Путь к файлу параметров навигации |
| `info_generator_params_file` | string | `/home/$USER/workspaces/isaac_ros-dev/src/isaac_ros_cloud_control/isaac_ros_vda5050_client_bringup/config/json_info_generator_params.yaml` | Путь к файлу параметров JSON Info Generator |
| `launch_rviz` | bool | `false` | Запускать RViz |


## Пробный для карты с офисом

ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  init_pose_x:=-6.0 \
  init_pose_y:=-1.0 \
  reconnect_period:=30 \
  use_sim_time:=true \
  mqtt_host_name:=185.55.57.82


```bash
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  namespace:=carter1 \
  ros_to_mqtt_name:=Carter1_RosToMqttBridge \
  mqtt_to_ros_name:=Carter1_MqttToRosBridge \
  init_pose_x:=-6.0 \
  init_pose_y:=-1.0 \
  major_version:=v2 \
  manufacturer:=RobotCompany \
  serial_number:=carter1 \
  reconnect_period:=30 \
  map:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/downloaded_maps/map.yaml \
  nav_params_file:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/navigation_params.yaml \
  use_namespace:=true \
  use_static_tf:=true \
  use_sim_time:=true \
  mqtt_host_name:=185.55.57.82 &
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  namespace:=carter2 \
  ros_to_mqtt_name:=Carter2_RosToMqttBridge \
  mqtt_to_ros_name:=Carter2_MqttToRosBridge \
  init_pose_x:=6.0 \
  init_pose_y:=-3.0 \
  major_version:=v2 \
  manufacturer:=RobotCompany \
  serial_number:=carter2 \
  reconnect_period:=30 \
  map:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/downloaded_maps/map.yaml \
  nav_params_file:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/navigation_params.yaml \
  use_namespace:=true \
  use_static_tf:=true \
  use_sim_time:=true \
  mqtt_host_name:=185.55.57.82 &
ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py \
  namespace:=carter3 \
  ros_to_mqtt_name:=Carter3_RosToMqttBridge \
  mqtt_to_ros_name:=Carter3_MqttToRosBridge \
  init_pose_x:=5.0 \
  init_pose_y:=-5.0 \
  major_version:=v2 \
  manufacturer:=RobotCompany \
  serial_number:=carter3 \
  reconnect_period:=30 \
  map:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/downloaded_maps/map.yaml \
  nav_params_file:=/workspaces/isaac_ros-dev/ros_ws/src/isaac_ros_cloud_control/navigation_params.yaml \
  use_namespace:=true \
  use_static_tf:=true \
  use_sim_time:=true \
  mqtt_host_name:=185.55.57.82 &
```


### Можно добавить recorder

ros_recorder:=true параметр при запуске mission client, при отправке миссии можно указать начало и остановку записи, что полезно, если данные с сенсоров нужно собрать и записать

## начало записи

{
  "robot": "carter01",
  "mission_tree": [
    {
      "name": "string",
      "parent": "root",
      "action": {
        "action_type": "start_recording",
        "action_parameters": {"path": "/tmp/data", "topics": "/rgb_left", "time":3}
      }
    }
  ],
  "timeout": 300,
  "deadline": "2022-10-07T00:21:31.112Z",
  "needs_canceled": false,
  "name": "mission01"
}

## конец записи

{
  "robot": "carter01",
  "mission_tree": [
    {
      "name": "string",
      "parent": "root",
      "action": {
        "action_type": "stop_recording"
      }
    }
  ],
  "timeout": 300,
  "deadline": "2022-10-07T00:21:31.112Z",
  "needs_canceled": false,
  "name": "mission02"
}



## Запуск контейнера

# Остановить старый контейнер
docker compose -p workspace -f ./docker/docker-compose.ros2.yml down

# Запустить новый
docker compose -p workspace -f ./docker/docker-compose.ros2.yml up -d

# Войти в контейнер (всё уже настроено)
docker exec -it vda5050_client /bin/bash