from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from nvidia_isaac_simulation.robots.wheeled import WheeledRobotSpawner


def test_resolve_asset_path_uses_ros_nova_carter_usd():
    with patch.object(WheeledRobotSpawner, "__init__", return_value=None):
        spawner = WheeledRobotSpawner.__new__(WheeledRobotSpawner)
        spawner.assets_root = "/assets"
        spawner.robot_type = "nova_carter"

    assert spawner._resolve_asset_path() == "/assets/Isaac/Samples/ROS2/Robots/Nova_Carter_ROS.usd"

