# TODO: 05_goal_sending

## Описание
Реализация программной отправки навигационных целей (`navigate_to_pose`) для каждого из роботов через кастомные Action Clients.

## Задачи
- [ ] **Создание структуры ROS 2 ноды `MultiRobotGoalSender`**
  - Подготовить файл `multi_robot_goal_sender.py` в пакете ROS 2.
  - Импортировать `NavigateToPose` из `nav2_msgs.action` и `ActionClient` из `rclpy.action`.
  - Отнаследоваться от `Node`.
- [ ] **Инициализация Action-клиентов**
  - В конструкторе создать словарь `self.clients = {}`.
  - В цикле по именам роботов (`'carter1'`, `'carter2'`) создать экшен-клиенты: `ActionClient(self, NavigateToPose, f'/{robot}/navigate_to_pose')`.
- [ ] **Формирование структуры целей (Goals)**
  - Создать словарь `self.goals = {'carter1': {'x': 2.0, 'y': 1.0, 'yaw': 0.0}, ...}`.
  - Написать метод `def send_goals(self)` для прохода по целям.
- [ ] **Отправка целей**
  - Создать сообщение цели `goal_msg = NavigateToPose.Goal()`.
  - Установить заголовок `goal_msg.pose.header.frame_id = 'map'` (глобальный фрейм).
  - Заполнить позицию `pose.position.x` и `pose.position.y`.
  - Преобразовать Yaw (Euler) в `quaternion`. Для ROS 2 можно использовать `tf_transformations.quaternion_from_euler` или встроенную математику: заполнить `orientation.z = sin(yaw/2)`, `orientation.w = cos(yaw/2)`.
- [ ] **Оркестрация и обработка обратной связи**
  - Дождаться старта серверов через `self.clients[robot].wait_for_server()`.
  - Отправить `client.send_goal_async(goal_msg)`.
  - Привязать callback'и (add_done_callback) для получения результатов (`get_result_async`).
- [ ] **Тестирование**
  - Запустить симуляцию -> `multi_robot_nav2.launch.py`.
  - Скомпилировать пакет `colcon build`.
  - Запустить ноду отправки `ros2 run <pkg_name> multi_robot_goal_sender`.
  - Проверить в `rviz2` или визуально в Isaac Sim, что роботы направляются к указанным координатам.
