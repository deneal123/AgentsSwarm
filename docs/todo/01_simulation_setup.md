# TODO: 01_simulation_setup

## Описание
В текущем репозитории уже существует базовая инициализация `AppCore` (в `src/nvidia_isaac_simulation/app.py`), парсинг параметров из `config/settings.toml` и класс спавна роботов `WheeledRobotSpawner` (в `src/nvidia_isaac_simulation/robots/wheeled.py`).
Однако, текущая реализация `WheeledRobotSpawner` не использует функционал пространств имен (`isaac:namespace`) и программное включение камер ROS 2, что обязательно для работы multi-robot SLAM.
Данный этап направлен на доработку `WheeledRobotSpawner` и `AppCore`.

## Задачи
- [x] **Доработка конфигурации симуляции `settings.toml`**
  - Синхронизировать конфиг с текущей реализацией в `src/nvidia_isaac_simulation/config/settings.toml`, где уже есть блок `[default.robots]`.
  - Добавить список стабильных имён роботов, например `names = ["carter1", "carter2"]`, чтобы спавнер получал предсказуемые namespace.
  - При инициализации приложения проверить, что `count` совпадает с длиной `names`; если нет, сразу падать с понятной ошибкой.
  - Если в будущем понадобятся разные профили роботов, вынести это в отдельную секцию, например `[default.robots.namespaces]` или `[default.robots.instances]`, но не смешивать с общими параметрами типа `spacing` и `z_offset`.
- [x] **Обновление пути к ассету `nova_carter.usd` (с настроенными ROS 2 нодами)**
  - В методе `_resolve_asset_path` класса `WheeledRobotSpawner` (`wheeled.py`) заменить базовый ассет Nova Carter на ROS-совместимый актив:
    `.../Isaac/Samples/ROS2/Robots/Nova_Carter_ROS.usd`.
  - Учитывать, что именно этот USD уже содержит подготовленные ROS 2/OmniGraph узлы, а не просто геометрию робота.
  - Проверить, что путь собирается из `get_assets_root_path()` и корректно работает в локальной установке Isaac Sim.
  - Для диагностики добавить временный `logger.info(...)` с итоговым путём ассета при первом спавне робота.
  - Зафиксировать это поведение маленьким unit-тестом на `_resolve_asset_path()` для `nova_carter`.
- [x] **Назначение ROS 2 Namespaces (`isaac:namespace`) при спавне**
  - В цикле метода `spawn_robots` (в `WheeledRobotSpawner`) после добавления прима (`prim=stage.GetPrimAtPath(prim_path)`):
    - Создать или обновить строковый атрибут: `prim.CreateAttribute("isaac:namespace", omni.usd.type.SdfValueTypeNames.String).Set(robot_name)`
    - Имя робота (`robot_name`) брать из переданного списка имен (напр., `names[i]`).
  - Проверить, что namespace выставляется на корневом `prim` сразу после `world.scene.add(...)`, до первого `world.reset()`.
  - Убедиться, что namespace не только задаёт префикс топиков, но и не конфликтует с текущей структурой `/World/Rovers/Rover_X`.
  - Если `robot_names` не заданы в конфиге, использовать fallback-имена, но зафиксировать их в коде как временный режим.
- [x] **Включение камер (Render Products) внутри `WheeledRobotSpawner`**
  - Добавить метод `_enable_camera_renders(self, robot_prim_path: str)`.
  - Метод должен использовать `stage.Traverse()` и находить графы `ActionGraph` внутри новосозданного пути робота.
  - Искать ноды `camera_render_product` (через `omni.graph.core.get_node_by_path()`) и устанавливать атрибут `inputs:enabled` в `True`.
  - Вызывать `_enable_camera_renders(prim_path)` для каждого заспавненного робота.
  - При необходимости добавить переключатель в конфиг, чтобы камеры можно было включать только для части сценариев (например, `enable_cameras = true`).
  - Если графов несколько, ограничиться только теми, что относятся к данному роботу, а не проходить всю сцену без фильтра по `robot_prim_path`.
  - Отдельно проверить, что включение камер не ломает headless-режим и не создаёт ошибки при отсутствии render context.
- [x] **Тестирование**
  - Запустить текущую точку входа проекта (`python -m nvidia_isaac_simulation start-sim` или соответствующий CLI проекта).
  - Проверить, что приложение стартует без ошибок уже на этапе `AppCore._spawn_default_robots()`.
  - В ROS 2 окружении выполнить `ros2 topic list` и убедиться, что изолированные топики для каждого робота действительно появились.
  - Дополнительно проверить, что у каждого робота есть уникальный namespace `carter1`, `carter2`, а не общий префикс по умолчанию.
