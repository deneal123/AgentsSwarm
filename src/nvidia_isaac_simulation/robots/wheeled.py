from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

from nvidia_isaac_simulation.robots.base import BaseRobotSpawner
from nvidia_isaac_simulation.config import settings
from nvidia_isaac_simulation.utils import get_logger

logger = get_logger(__name__)


class WheeledRobotSpawner(BaseRobotSpawner):
    """Спавнер колёсных роботов (Carter/NovaCarter) с сеточной раскладкой."""

    def __init__(
        self,
        world,
        robot_type: str = "carter",
        spacing: float = 2.5,
        z_offset: float = 0.5,
        robot_names: Optional[Sequence[str]] = None,
        enable_cameras: bool = True,
        base_prim: str = "/World/Rovers",
    ) -> None:
        super().__init__(world)
        self.robot_type = robot_type.lower()
        self.spacing = spacing
        self.z_offset = z_offset
        self.robot_names = list(robot_names) if robot_names is not None else []
        self.enable_cameras = enable_cameras
        self.base_prim = base_prim.rstrip("/")
        from isaacsim.storage.native import get_assets_root_path

        self.assets_root = get_assets_root_path()
        if not self.assets_root:
            raise RuntimeError("Isaac Sim assets root path was not found. Check installation.")
        self.asset_path = self._resolve_asset_path()

    @staticmethod
    def validate_robot_names_count(count: int, robot_names: Optional[Sequence[str]]) -> List[str]:
        names = list(robot_names) if robot_names is not None else []
        if names and len(names) != count:
            raise ValueError("Length of robot_names must match count")
        if names:
            return names
        return [f"robot_{i}" for i in range(count)]

    def _validate_robot_names(self, count: int) -> List[str]:
        return self.validate_robot_names_count(count, self.robot_names)

    def _safe_set_namespace(self, prim_path: str, robot_name: str) -> None:
        try:
            self._set_namespace(prim_path, robot_name)
        except Exception as exc:
            logger.warning(
                "[WheeledRobotSpawner] Failed to set namespace for %s (%s): %s",
                prim_path,
                robot_name,
                exc,
            )

    def spawn_robots(
        self,
        count: int,
        positions: Optional[Sequence[Tuple[float, float, float]]] = None,
    ) -> List[WheeledRobot]:
        if positions is not None and len(positions) != count:
            raise ValueError("Length of positions must match count")

        names = self._validate_robot_names(count)

        robots: List[WheeledRobot] = []
        for i in range(count):
            pos = positions[i] if positions else self._grid_position(i, count)
            robot_name = names[i]
            prim_path = f"{self.base_prim}/{robot_name}"
            robot = self._create_robot(prim_path=prim_path, position=pos)
            self._safe_set_namespace(prim_path, robot_name)
            if self.enable_cameras:
                self._enable_camera_renders(prim_path)
            robots.append(robot)
            logger.info(
                "[WheeledRobotSpawner] Spawned %s at %s (prim=%s)", self.robot_type, np.round(pos, 3), prim_path
            )

        try:
            self.world.reset()
        except Exception:
            pass
        return robots

    def _create_robot(self, prim_path: str, position: Tuple[float, float, float]) -> WheeledRobot:
        from isaacsim.robot.wheeled_robots.robots import WheeledRobot

        return self.world.scene.add(
            WheeledRobot(
                prim_path=prim_path,
                name=prim_path.rsplit("/", maxsplit=1)[-1],
                wheel_dof_names=["left_wheel", "right_wheel"],
                create_robot=True,
                usd_path=self.asset_path,
                position=np.array(position, dtype=float),
            )
        )

    def _set_namespace(self, prim_path: str, robot_name: str) -> None:
        import omni.usd
        from pxr import Sdf

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not found for namespace assignment: {prim_path}")

        namespace_attr = prim.GetAttribute("isaac:namespace")
        if not namespace_attr:
            namespace_attr = prim.CreateAttribute("isaac:namespace", Sdf.ValueTypeNames.String)
        namespace_attr.Set(robot_name)

    def _enable_camera_renders(self, robot_prim_path: str) -> None:
        import omni.graph.core as og
        import omni.usd

        stage = omni.usd.get_context().get_stage()
        for prim in stage.Traverse():
            path = prim.GetPath().pathString
            if not path.startswith(robot_prim_path):
                continue
            type_name = prim.GetTypeName()
            name = prim.GetName()
            if type_name != "ActionGraph" and "ActionGraph" not in name and "_hawk" not in path:
                continue

            for child in prim.GetChildren():
                if "camera_render_product" not in child.GetName():
                    continue
                child_path = child.GetPath().pathString
                node = og.get_node_by_path(child_path)
                if node is None:
                    logger.debug("[WheeledRobotSpawner] camera_render_product node not found: %s", child_path)
                    continue

                try:
                    node.set_attribute("inputs:enabled", True)
                except Exception as exc:
                    logger.warning("[WheeledRobotSpawner] Failed to enable camera node %s: %s", child_path, exc)

    def _grid_position(self, index: int, total: int) -> Tuple[float, float, float]:
        cols = math.ceil(math.sqrt(total))
        rows = math.ceil(total / cols)
        row = index // cols
        col = index % cols
        x = (col - (cols - 1) / 2) * self.spacing
        y = (row - (rows - 1) / 2) * self.spacing
        z = self.z_offset
        return (x, y, z)

    def _resolve_asset_path(self) -> str:
        root = self.assets_root.rstrip("/")
        if self.robot_type in ("carter", "carter_v1"):
            return root + "/Isaac/Robots/NVIDIA/Carter/carter_v1_physx_lidar.usd"
        if self.robot_type in ("nova_carter", "novacarter"):
            asset_path = root + "/Isaac/Samples/ROS2/Robots/Nova_Carter_ROS.usd"
            logger.info("[WheeledRobotSpawner] Using ROS asset for Nova Carter: %s", asset_path)
            return asset_path
        logger.warning("[WheeledRobotSpawner] Unknown robot type '%s', fallback to Carter", self.robot_type)
        return root + "/Isaac/Robots/NVIDIA/Carter/carter_v1_physx_lidar.usd"


def spawn_wheeled_robots(world, count: int) -> List[WheeledRobot]:
    robot_cfg = getattr(settings, "robots", {})
    robot_type = getattr(robot_cfg, "type", "carter")
    spacing = float(getattr(robot_cfg, "spacing", 2.5))
    z_offset = float(getattr(robot_cfg, "z_offset", 0.5))

    spawner = WheeledRobotSpawner(
        world=world,
        robot_type=robot_type,
        spacing=spacing,
        z_offset=z_offset,
    )
    return spawner.spawn_robots(count)
