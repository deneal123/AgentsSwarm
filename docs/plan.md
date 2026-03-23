Реализация мульти-роботной навигации с SLAM и Mission Dispatch в NVIDIA Isaac Sim
В данном руководстве описан подход к интеграции нескольких роботов Nova Carter в симуляции Isaac Sim с использованием ROS 2, навигации Nav2, SLAM (построения карты), автоматической отправки целей и системы миссий через isaac_mission_dispatch. Система подразумевает динамическую генерацию мира, построение карты в процессе навигации и централизованное управление миссиями через MCP-сервер (ros-msp-server) и оркестратор на основе OpenAI Agents SDK.

1. Подготовка симуляции: несколько роботов Nova Carter с корректными пространствами имён
Актив Nova_Carter_ROS.usd уже содержит настроенные Omnigraph для публикации сенсорных данных и одометрии. Для каждого робота необходимо назначить уникальное пространство имён, чтобы топики и ноды были изолированы.

Создание экземпляров роботов в сцене:

Загрузите основной актив Nova_Carter_ROS.usd из папки /Isaac/Samples/ROS2/Robots/.

Для каждого робота (например, carter1, carter2) добавьте ссылку на этот USD в сцену.

Для каждого экземпляра установите атрибут isaac:namespace на корневом приме (например, /World/carter1). Это автоматически добавит префикс ко всем ROS-топикам, издаваемым роботом (согласно правилам, описанным в Automatic ROS 2 Namespace Generation).

Пример скрипта добавления двух роботов с пространствами имён (выполнять в Script Editor):

python
import omni.usd
from isaacsim.core.utils.stage import add_reference_to_stage

stage = omni.usd.get_context().get_stage()
assets_root = "/Isaac"  # путь к Nucleus
robot_usd = assets_root + "/Samples/ROS2/Robots/Nova_Carter_ROS.usd"

# Добавляем роботов
robots = ["carter1", "carter2"]
for name in robots:
    path = f"/World/{name}"
    add_reference_to_stage(robot_usd, path)
    # Устанавливаем атрибут isaac:namespace на корневом приме
    prim = stage.GetPrimAtPath(path)
    if not prim.HasAttribute("isaac:namespace"):
        prim.CreateAttribute("isaac:namespace", omni.usd.type.SdfValueTypeNames.String).Set(name)
    else:
        prim.GetAttribute("isaac:namespace").Set(name)
После этого топики будут иметь вид:

/carter1/scan

/carter1/odom

/carter1/camera_left/rgb
и т.д.

Включение камер:
В графах Nova Carter камеры отключены для производительности. Чтобы их активировать, найдите в Stage под каждым роботом узлы _hawk (например, /World/carter1/Nova_Carter_ROS/_hawk) и в их ActionGraph включите ноды _camera_render_product. Сделать это можно программно:

python
def enable_camera_renders(robot_prim_path):
    stage = omni.usd.get_context().get_stage()
    # Ищем все ActionGraph внутри робота
    for prim in stage.Traverse():
        if prim.GetPath().pathString.startswith(robot_prim_path) and prim.GetTypeName() == "ActionGraph":
            # Внутри графа ищем ноду с именем *_camera_render_product
            for child in prim.GetChildren():
                if "camera_render_product" in child.GetName():
                    # Включаем ноду: устанавливаем атрибут enabled = True
                    node = omni.graph.core.get_node_by_path(child.GetPath())
                    if node:
                        node.set_attribute("inputs:enabled", True)

for name in robots:
    enable_camera_renders(f"/World/{name}/Nova_Carter_ROS")
2. Настройка Nav2 для нескольких роботов
Для каждого робота необходимо запустить собственный стек Nav2 с использованием пространства имён. В Isaac Sim уже есть примеры для двух-трёх роботов (например, multiple_robot_carter_navigation_hospital.launch.py).

Создадим launch-файл для запуска Nav2 для двух роботов:

python
# multi_robot_nav2.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():
    robots = ["carter1", "carter2"]
    nodes = []
    for robot in robots:
        # Запускаем Nav2 для каждого робота со своим пространством имён
        nav2_bringup = Node(
            package='nav2_bringup',
            executable='bringup_launch.py',
            namespace=robot,
            arguments=['use_sim_time:=True'],
            parameters=[{'use_sim_time': True}],
        )
        # Дополнительные ноды, например, map_server (если нужна глобальная карта)
        nodes.append(nav2_bringup)
    return LaunchDescription(nodes)
Но более полный вариант можно взять из примера carter_navigation/multiple_robot_carter_navigation_hospital.launch.py, где дополнительно настраиваются параметры карты, AMCL и прочее.

Важно: для использования SLAM вместо готовой карты, Nav2 должен получать карту от SLAM-ноды. Это означает, что нужно отключить map_server и настроить плагин глобального планировщика на использование топика /map от SLAM.

3. SLAM (построение карты) для каждого робота
Используем isaac_ros_visual_slam (cuVSLAM), который поддерживает мультикамерную настройку и может строить карту в реальном времени. Запускаем для каждого робота с соответствующим пространством имён.

Запуск SLAM для одного робота (в составе launch-файла):

python
# Запуск Visual SLAM для одного робота
slam_node = Node(
    package='isaac_ros_visual_slam',
    executable='isaac_ros_visual_slam_node',
    namespace=robot_namespace,
    parameters=[{
        'use_sim_time': True,
        'camera0_topic': f'/{robot_namespace}/front_stereo_camera/left/image_rect',
        'camera0_info_topic': f'/{robot_namespace}/front_stereo_camera/left/camera_info_rect',
        'camera1_topic': f'/{robot_namespace}/front_stereo_camera/right/image_rect',
        'camera1_info_topic': f'/{robot_namespace}/front_stereo_camera/right/camera_info_rect',
        # Для использования лидара можно добавить параметры, но cuVSLAM по умолчанию работает с камерами
    }],
    remappings=[
        ('/visual_slam/odometry', f'/{robot_namespace}/odometry/slam'),
        ('/visual_slam/map', f'/{robot_namespace}/map'),
    ]
)
Для публикации карты в формате occupancy grid (для Nav2) можно использовать nvblox или slam_toolbox. nvblox умеет строить 2D карту из глубины и лидаров. Запуск nvblox для каждого робота аналогичен.

Важно: для навигации с одновременным построением карты Nav2 должен использовать топик карты от SLAM-ноды, а не статическую карту. Это настраивается в конфиге Nav2 (например, через параметр map_topic).

4. Динамическое создание мира и карты
Динамический мир: в Isaac Sim можно загружать разные окружения (склад, больница) через загрузку USD-ассетов. Чтобы мир генерировался динамически (например, каждый запуск новая конфигурация), можно использовать скрипты, создающие препятствия на основе правил.

Пример добавления случайных препятствий:

python
import random
from pxr import UsdGeom, Gf

def add_random_obstacles(stage, num_obstacles=10):
    for i in range(num_obstacles):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        path = f"/World/Obstacle_{i}"
        cube = UsdGeom.Cube.Define(stage, path)
        cube.AddTranslateOp().Set(Gf.Vec3d(x, y, 0.5))
        cube.GetSizeAttr().Set(0.5)
        # Добавляем физику и коллизию (если нужно)
Построение карты: для SLAM начальная карта пуста, она будет заполняться по мере движения роботов. Если нужно использовать предварительно сгенерированную карту для ускорения, можно сгенерировать её из сцены с помощью Occupancy Map Generator (инструмент в Isaac Sim). Скрипт для генерации карты из сцены можно найти в туториалах (например, через omni.kit.occupancy_map).

5. Программная отправка целей для нескольких роботов
Пакет isaac_ros_navigation_goal позволяет отправлять цели в Nav2. Для нескольких роботов нужно создать отдельные экземпляры ноды или адаптировать launch-файл.

Пример Python-ноды для отправки целей разным роботам:

python
import rclpy
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient

class MultiRobotGoalSender(Node):
    def __init__(self):
        super().__init__('multi_robot_goal_sender')
        self.clients = {}
        self.goals = {
            'carter1': {'x': 2.0, 'y': 1.0, 'yaw': 0.0},
            'carter2': {'x': -2.0, 'y': 1.5, 'yaw': 1.57},
        }
        for robot in self.goals.keys():
            action_name = f'/{robot}/navigate_to_pose'
            self.clients[robot] = ActionClient(self, NavigateToPose, action_name)

    def send_goals(self):
        for robot, pose_data in self.goals.items():
            goal = NavigateToPose.Goal()
            goal.pose.header.frame_id = 'map'
            goal.pose.pose.position.x = pose_data['x']
            goal.pose.pose.position.y = pose_data['y']
            goal.pose.pose.orientation.z = pose_data['yaw']
            # ориентацию нужно кватернионом, упрощённо
            self.clients[robot].wait_for_server()
            self.clients[robot].send_goal_async(goal)

def main(args=None):
    rclpy.init(args=args)
    sender = MultiRobotGoalSender()
    sender.send_goals()
    rclpy.spin(sender)
    sender.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
6. Интеграция Mission Dispatch (VDA5050)
isaac_ros_mission_client позволяет роботу получать миссии через MQTT и выполнять последовательности действий (движение, специальные действия). Для нескольких роботов каждый запускает свой клиент с уникальными идентификаторами (manufacturer, serial_number).

Запуск mission client для каждого робота (в launch-файле):

python
for robot in robots:
    mission_client = Node(
        package='isaac_ros_vda5050_client_bringup',
        executable='isaac_ros_vda5050_client.launch.py',
        namespace=robot,
        arguments=[
            f'namespace:={robot}',
            f'serial_number:={robot}',
            'manufacturer:=RobotCompany',
            'mqtt_host_name:=localhost',  # или адрес брокера
        ],
    )
Серверная часть isaac_mission_dispatch обычно представляет собой веб-сервис (например, FastAPI) с Swagger-документацией. Он получает HTTP-запросы с описанием миссий и отправляет их через MQTT соответствующим роботам.

Пример REST-запроса к mission dispatch для отправки миссии роботу carter1:

json
POST /api/v1/missions
{
  "robot": "carter1",
  "mission_tree": [
    {
      "parent": "root",
      "action": {
        "action_type": "start_recording",
        "action_parameters": {"path": "/tmp/data", "topics": "/rgb_left", "time": 3}
      }
    },
    {
      "parent": "root",
      "route": {
        "waypoints": [
          {"x": 1.0, "y": 0.0, "theta": 0.0},
          {"x": 2.0, "y": 1.0, "theta": 1.57}
        ]
      }
    }
  ]
}
7. Интеграция с MCP-сервером (ros-msp-server) и оркестратором
ros-msp-server предоставляет инструменты для взаимодействия с ROS 2 (списки топиков, нод, вызовы сервисов, действия). Чтобы добавить управление миссиями, можно расширить MCP-сервер новыми инструментами, вызывающими API mission dispatch.

Пример инструмента для отправки миссии через MCP (используя HTTP-запрос):

python
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

server = Server("ros-mission-dispatch")

@server.list_tools()
async def handle_list_tools():
    return [
        {
            "name": "send_mission",
            "description": "Send a mission to a robot",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "robot": {"type": "string"},
                    "mission_tree": {"type": "array"},
                    "timeout": {"type": "integer"}
                },
                "required": ["robot", "mission_tree"]
            }
        }
    ]

@server.call_tool()
async def handle_call_tool(name, arguments):
    if name == "send_mission":
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://mission-dispatch-service/api/v1/missions",
                json={
                    "robot": arguments["robot"],
                    "mission_tree": arguments["mission_tree"],
                    "timeout": arguments.get("timeout", 300)
                }
            )
            return [{"type": "text", "text": f"Mission sent: {response.text}"}]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(server_name="ros-mission-dispatch", server_version="0.1.0")
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
Оркестратор (агент на OpenAI Agents SDK) может использовать этот инструмент для выдачи миссий роботам.

8. Сводка шагов для запуска полной системы
Запуск симуляции Isaac Sim в headless режиме с несколькими роботами (используя скрипты выше).

Запуск ROS 2 компонентов для каждого робота: Nav2, SLAM, mission client (можно через один launch-файл).

Запуск MQTT брокера (например, Mosquitto) и mission dispatch сервера.

Запуск ros-msp-server с расширенными инструментами.

Запуск оркестратора (агент на Python с OpenAI Agents SDK), который использует инструменты MCP для управления роботами.

Заключение
Данный подход позволяет создать масштабируемую систему управления роем роботов в симуляции Isaac Sim с полным циклом: динамический мир, SLAM, навигация Nav2, управление миссиями через VDA5050 и интеграция с LLM-агентами через MCP. Ключевые моменты – корректное использование пространств имён в ROS 2, настройка Omnigraph для публикации сенсоров, а также связка mission dispatch с MCP-сервером. Приведённые фрагменты кода могут быть адаптированы под конкретную конфигурацию.