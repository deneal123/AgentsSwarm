# TODO: 02_nav2_multi_robot

## Описание
Для того чтобы роботы корректно работали в одном ROS-окружении, для каждого из них необходимо запустить независимый стек Nav2 (навигацию) со своим пространством имён. Важная особенность: Nav2 будет использовать динамическую карту со SLAM, а не статическую.

## Задачи
- [ ] **Подготовка рабочего пространства ROS 2**
  - Убедиться, что в ROS 2 workspace установлен и доступен `nav2_bringup`, а также базовый стек Nav2 (`nav2_bt_navigator`, `nav2_controller`, `nav2_planner`, `nav2_costmap_2d`).
  - Определить, где будет жить multi-robot launch: либо в отдельном пакете `isaac_nav_multi`, либо внутри текущего orchestration-проекта как отдельный launch-слой.
  - Сразу зафиксировать соглашение по именам namespace: `carter1`, `carter2`, чтобы они совпадали с именами в `01_simulation_setup.md`.
- [ ] **Создание Launch-файла для Nav2**
  - Создать новый `multi_robot_nav2.launch.py` на базе `launch.LaunchDescription`.
  - Импортировать `Node`, `DeclareLaunchArgument`, `LaunchConfiguration`, а также helper-функции для сборки параметров.
  - Задать список имен роботов: `robots = ["carter1", "carter2"]` и использовать его как единый источник истины для всех узлов.
  - Сгенерировать `LaunchDescription` через накопление `nodes = []` и возврат в конце функции `generate_launch_description()`.
- [ ] **Настройка `nav2_bringup` (в цикле для каждого `robot`)**
  - Для каждого робота в цикле создать отдельный набор Nav2-нод в namespace `robot`.
  - Передавать `use_sim_time=True` во все Nav2-компоненты, чтобы синхронизироваться с симуляцией.
  - Определить набор базовых параметров: `bt_navigator`, `controller_server`, `planner_server`, `smoother_server`, `behavior_server`, `waypoint_follower`.
  - Не пытаться запускать `bringup_launch.py` как обычный executable Node; вместо этого организовать либо `IncludeLaunchDescription`, либо явный запуск набора Nav2-нод с параметрами.
- [ ] **Отключение `map_server` (подготовка к SLAM)**
  - Убрать зависимость от статического `map_server`, потому что карта будет публиковаться SLAM-нодой.
  - В YAML-параметрах оставить только те слои costmap, которые реально нужны для динамической навигации: `obstacle_layer`, `inflation_layer`.
  - В `global_costmap` и `local_costmap` явно задать подписку на карту робота: `map_topic: f'/{robot}/map'`.
  - Проверить, что `keepout`/`speed_filter`-слои, если они будут добавлены позже, не завязаны на статическую карту.
- [ ] **Настройка TF-деревьев (tf_transforms)**
  - Зафиксировать ожидаемую TF-цепочку: `map -> odom -> base_link` внутри namespace каждого робота.
  - Указать `robot_base_frame`, `odom_frame` и `global_frame` в параметрах Nav2 с учётом namespace.
  - Если SLAM публикует `map -> odom`, не включать AMCL, чтобы не было конфликтов источников TF.
  - Проверить, что все frame ids в параметрах и в сообщениях совпадают с namespace-структурой робота.
- [ ] **Интеграция с локальными сенсорами**
  - Настроить `obstacle_layer` на lidar-топик конкретного робота: `scan_topic: f'/{robot}/scan'`.
  - Если используются depth-камеры, заранее зафиксировать, какие топики будут преобразованы в costmap source.
  - Убедиться, что все локальные сенсоры публикуются с namespace из `01_simulation_setup.md`.
- [ ] **Тестирование**
  - Запустить `ros2 launch <имя_пакета> multi_robot_nav2.launch.py` после старта симуляции.
  - Проверить, что action server `/<namespace>/navigate_to_pose` поднят для каждого робота.
  - Проверить `ros2 topic echo /tf --once` или `view_frames`, чтобы убедиться в отсутствии конфликтов `map/odom/base_link`.
  - Если что-то не поднимается, сначала проверять namespace и наличие SLAM карты, а уже потом логи Nav2.
