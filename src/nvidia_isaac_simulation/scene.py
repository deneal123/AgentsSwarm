from __future__ import annotations

from pathlib import Path
from typing import Optional

from nvidia_isaac_simulation.config import settings
from nvidia_isaac_simulation.utils import get_logger

logger = get_logger(__name__)


class SceneSetup:
    """
    Utility for configuring the simulation world, loading a base environment,
    and applying physics settings (dt, substeps, GPU PhysX).
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

    def initialize_world(self):
        """Create and configure the `World` instance with a default environment."""
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import add_reference_to_stage
        from isaacsim.storage.native import get_assets_root_path

        assets_root_path = get_assets_root_path()
        if not assets_root_path:
            raise RuntimeError("Isaac Sim assets root path was not found. Check installation.")

        env_usd_path, is_remote = self._resolve_env_path(assets_root_path)
        logger.info(
            "[SceneSetup] Создание мира: physics_dt=%.6f, rendering_dt=%.6f, substeps=%s, gpu_physx=%s",
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

        if self.substeps and hasattr(physics_context, "set_substeps"):
            try:
                physics_context.set_substeps(self.substeps)
                logger.debug("[SceneSetup] Установлено число подшагов: %s", self.substeps)
            except Exception as exc:  # pragma: no cover - API robustness
                logger.warning("[SceneSetup] Не удалось применить substeps=%s: %s", self.substeps, exc)

        if self.use_gpu_physx and hasattr(physics_context, "enable_gpu_dynamics"):
            try:
                physics_context.enable_gpu_dynamics(True)
                logger.info("[SceneSetup] GPU PhysX включен")
            except Exception as exc:  # pragma: no cover
                logger.warning("[SceneSetup] Не удалось включить GPU PhysX: %s", exc)

        try:
            if is_remote and env_usd_path:
                add_reference_to_stage(usd_path=env_usd_path, prim_path="/World/Environment")
                logger.info("[SceneSetup] Загружено удалённое окружение: %s", env_usd_path)
            elif env_usd_path and env_usd_path.exists():
                add_reference_to_stage(usd_path=str(env_usd_path), prim_path="/World/Environment")
                logger.info("[SceneSetup] Загружено окружение: %s", env_usd_path)
            else:
                raise FileNotFoundError(env_usd_path)
        except Exception as exc:
            logger.warning(
                "[SceneSetup] Не удалось загрузить окружение (%s). Добавляем Ground Plane.", exc
            )
            world.scene.add_default_ground_plane()

        try:
            physics_context.initialize_physics()
        except AttributeError:
            initialize = getattr(world, "initialize_physics", None)
            if callable(initialize):
                initialize()

        world.reset()
        return world

    def _resolve_env_path(self, assets_root_path: str) -> tuple[Optional[Path | str], bool]:
        """Return path/url to the environment USD and whether it's remote."""

        if assets_root_path.startswith("http"):
            url = assets_root_path.rstrip("/") + "/" + self.environment_usd.lstrip("/")
            logger.debug("[SceneSetup] Получен URL ассетов: %s", url)
            return url, True

        env_path = Path(assets_root_path) / self.environment_usd
        return env_path, False


def build_default_world() -> "World":
    """Convenience helper that uses configuration defaults to create a world."""
    return SceneSetup().initialize_world()
