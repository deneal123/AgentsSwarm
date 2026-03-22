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
        base_prim: str = "/World/Rovers",
    ) -> None:
        super().__init__(world)
        self.robot_type = robot_type.lower()
        self.spacing = spacing
        self.z_offset = z_offset
        self.base_prim = base_prim.rstrip("/")
        from isaacsim.storage.native import get_assets_root_path

        self.assets_root = get_assets_root_path()
        if not self.assets_root:
            raise RuntimeError("Isaac Sim assets root path was not found. Check installation.")
        self.asset_path = self._resolve_asset_path()

    def spawn_robots(
        self,
        count: int,
        positions: Optional[Sequence[Tuple[float, float, float]]] = None,
    ) -> List[WheeledRobot]:
        if positions is not None and len(positions) != count:
            raise ValueError("Length of positions must match count")

        robots: List[WheeledRobot] = []
        for i in range(count):
            pos = positions[i] if positions else self._grid_position(i, count)
            prim_path = f"{self.base_prim}/Rover_{i}"
            robot = self._create_robot(prim_path=prim_path, position=pos)
            robots.append(robot)
            logger.info(
                "[WheeledRobotSpawner] Spawned %s at %s (prim=%s)", self.robot_type, np.round(pos, 3), prim_path
            )

        try:
            self.world.reset()
        except Exception:
            pass
        return robots

    # ------------ helpers ------------
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
            return root + "/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
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
