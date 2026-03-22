from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from nvidia_isaac_simulation.scene.base import BaseSceneBuilder
from nvidia_isaac_simulation.config import settings
from nvidia_isaac_simulation.utils import get_logger

logger = get_logger(__name__)


class SceneBuilder(BaseSceneBuilder):
    """Создание мира с окружением и настройками физики.

    Параметры берутся из settings, но могут быть переопределены через аргументы
    конструктора для сценариев/миссий.
    """

    def __init__(
        self,
        physics_dt: Optional[float] = None,
        rendering_dt: Optional[float] = None,
        substeps: Optional[int] = None,
        use_gpu_physx: Optional[bool] = None,
        environment_usd: Optional[str] = None,
    ) -> None:
        sim_settings = settings.simulation
        self.physics_dt = physics_dt if physics_dt is not None else float(sim_settings.physics_dt)
        self.rendering_dt = rendering_dt if rendering_dt is not None else float(sim_settings.rendering_dt)
        self.substeps = substeps if substeps is not None else int(sim_settings.substeps)
        self.use_gpu_physx = use_gpu_physx if use_gpu_physx is not None else bool(sim_settings.use_gpu_physx)
        self.environment_usd = environment_usd or str(sim_settings.environment_usd)

    def build(self) -> World:
        from isaacsim.core.api import World
        from isaacsim.storage.native import get_assets_root_path

        assets_root_path = get_assets_root_path()
        if not assets_root_path:
            raise RuntimeError("Isaac Sim assets root path was not found. Check installation.")

        env_usd_path, is_remote = self._resolve_env_path(assets_root_path)
        logger.info(
            "[SceneBuilder] Создание мира: physics_dt=%.6f, rendering_dt=%.6f, substeps=%s, gpu_physx=%s",
            self.physics_dt,
            self.rendering_dt,
            self.substeps,
            self.use_gpu_physx,
        )

        world = World(
            stage_units_in_meters=1.0,
            physics_dt=self.physics_dt,
            rendering_dt=self.rendering_dt,
        )

        physics_context = world.get_physics_context()
        gravity = getattr(settings.simulation, "gravity", None)
        if gravity is not None:
            try:
                gravity_value: float
                ignored_xy = None
                if isinstance(gravity, (list, tuple)):
                    if len(gravity) != 3:
                        raise ValueError("gravity must have 3 components when provided as a sequence")
                    ignored_xy = (gravity[0], gravity[1])
                    gravity_value = float(gravity[2])
                else:
                    gravity_value = float(gravity)

                # Isaac ожидает отрицательное значение для направления вниз.
                if gravity_value > 0:
                    gravity_value = -abs(gravity_value)

                physics_context.set_gravity(gravity_value)
                if ignored_xy:
                    logger.info(
                        "[SceneBuilder] Установлена гравитация по Z=%s (XY игнорируются API): %s",
                        gravity_value,
                        ignored_xy,
                    )
                else:
                    logger.info("[SceneBuilder] Установлена гравитация: %s", gravity_value)
            except Exception as exc:
                logger.warning("[SceneBuilder] Не удалось установить гравитацию %s: %s", gravity, exc)
        if self.substeps and hasattr(physics_context, "set_substeps"):
            try:
                physics_context.set_substeps(self.substeps)
            except Exception as exc:
                logger.warning("[SceneBuilder] Не удалось применить substeps=%s: %s", self.substeps, exc)

        if self.use_gpu_physx and hasattr(physics_context, "enable_gpu_dynamics"):
            try:
                physics_context.enable_gpu_dynamics(True)
                logger.info("[SceneBuilder] GPU PhysX включен")
            except Exception as exc:
                logger.warning("[SceneBuilder] Не удалось включить GPU PhysX: %s", exc)

        self._attach_environment(world, env_usd_path, is_remote)

        try:
            physics_context.initialize_physics()
        except AttributeError:
            initialize = getattr(world, "initialize_physics", None)
            if callable(initialize):
                initialize()

        world.reset()
        return world

    def _attach_environment(self, world: "World", env_usd_path: Optional[Path | str], is_remote: bool) -> None:
        from isaacsim.core.utils.stage import add_reference_to_stage
        try:
            if is_remote and env_usd_path:
                add_reference_to_stage(usd_path=env_usd_path, prim_path="/World/Environment")
                logger.info("[SceneBuilder] Загружено удалённое окружение: %s", env_usd_path)
            elif env_usd_path and isinstance(env_usd_path, Path) and env_usd_path.exists():
                add_reference_to_stage(usd_path=str(env_usd_path), prim_path="/World/Environment")
                logger.info("[SceneBuilder] Загружено окружение: %s", env_usd_path)
            else:
                raise FileNotFoundError(env_usd_path)
        except Exception as exc:
            logger.warning("[SceneBuilder] Не удалось загрузить окружение (%s). Добавляем Ground Plane.", exc)
            world.scene.add_default_ground_plane()

    def _resolve_env_path(self, assets_root_path: str) -> Tuple[Optional[Path | str], bool]:
        if assets_root_path.startswith("http"):
            url = assets_root_path.rstrip("/") + "/" + self.environment_usd.lstrip("/")
            logger.debug("[SceneBuilder] Получен URL ассетов: %s", url)
            return url, True

        env_path = Path(assets_root_path) / self.environment_usd
        return env_path, False


def build_default_world() -> World:
    """Convenience helper that uses configuration defaults to create a world."""
    return SceneBuilder().build()
