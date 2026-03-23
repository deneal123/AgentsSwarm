# TODO: 03_slam_setup

## Описание
Каждый робот должен строить карту окружения динамически с помощью визуального SLAM (cuVSLAM от NVIDIA) или nvblox в рамках своего пространства имён.

## Задачи
- [ ] **Настройка пакетов SLAM**
  - Использовать пакет `isaac_ros_visual_slam` в ROS 2 ws.
  - Убедиться, что он установлен и скомпилирован (или доступен в докер-образе `isaac_ros_dev`).
- [ ] **Создание Launch-включения cuVSLAM**
  - Добавить `Node` конфигурацию для `isaac_ros_visual_slam_node` внутрь общего файла `multi_robot_nav2.launch.py` (или в отдельный launch-скрипт).
  - Настроить `namespace=robot_namespace`.
  - Установить параметр `use_sim_time = True`.
- [ ] **Подписка на топики мультикамерной системы**
  - Задать `camera0_topic = f'/{robot_namespace}/front_stereo_camera/left/image_rect'`.
  - Задать `camera0_info_topic = f'/{robot_namespace}/front_stereo_camera/left/camera_info_rect'`.
  - Задать аналогичные топики для `camera1_topic` и `camera1_info_topic` (`right`).
- [ ] **Ремаппинг (Remappings) топиков SLAM вывода**
  - Добавить `remappings=[('/visual_slam/odometry', f'/{robot_namespace}/odometry/slam')]`.
  - Настроить публикацию карты: `remappings=[('/visual_slam/map', f'/{robot_namespace}/map')]`.
- [ ] **Дерево трансформаций (TF) и фреймы**
  - Настроить `base_frame` для cuVSLAM равным `base_link` (или локальному кареточному фрейму Carter).
  - Настроить `odom_frame` равным `odom` (в контексте namespace) и `map_frame` равным `map` (в контексте namespace).
  - Задать публикацию TF так, чтобы SLAM публиковал трансформацию `map -> odom`.
- [ ] **Тестирование**
  - Запустить симуляцию + Nav2/SLAM стек.
  - Поднять `rviz2`.
  - Настроить Fixed Frame на `map` (например, `carter1/map`).
  - Добавить `Map` display, указав топик `/<namespace>/map`.
  - После движения робота в симуляторе через `teleop`, проверить что `cuVSLAM` строит и отображает сетку Occupancy Grid.
