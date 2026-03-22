import os
from pathlib import Path

from nvidia_isaac_simulation.config import settings, PROJECT_ROOT
from nvidia_isaac_simulation.scene import SceneSetup
from nvidia_isaac_simulation.utils import get_logger
from isaacsim.simulation_app import SimulationApp

logger = get_logger(__name__)

class AppCore:
    def __init__(self):
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_envs()
        self.log_dir = log_dir
        self._prev_cwd = Path.cwd()
        os.chdir(log_dir)

        self.simulation_app = SimulationApp({"headless": settings.simulation.headless})
        self._setup_settings()
        self.world = self._initialize_world()
    
    def _setup_envs(self):
        os.environ["ACCEPT_EULA"] = "Y"
        os.environ.setdefault("CARB_LOGS", str(log_dir))
        os.environ.setdefault("OMNI_APP_LOG_DIR", str(log_dir))
        os.environ.setdefault("NV_STREAMER_LOG_DIR", str(log_dir))
        os.environ["OMNI_DISABLE_AUDIO"] = "1"
       
    def _setup_settings(self):
        signal_port = int(settings.WEBRTC__SIGNALER_PORT)
        stream_port = int(settings.WEBRTC__STREAMING_PORT)
        public_ip = str(settings.WEBRTC__PUBLIC_IP)

        self.simulation_app.set_setting("/log/file", str(self.log_dir / "nvstreamer.log"))
        self.simulation_app.set_setting("/log/fileAppend", True)

        logger.info(f"[AppCore] Включение Livestream. signal={signal_port}, stream={stream_port}, publicIp='{public_ip}'")
        from isaacsim.core.utils.extensions import enable_extension

        for ext in [
            "omni.kit.livestream.core",
            "omni.kit.livestream.messaging",
            "omni.kit.livestream.app",
            "omni.kit.livestream.webrtc",
        ]:
            try:
                enable_extension(ext)
                logger.debug(f"[AppCore] Extension enabled: {ext}")
            except Exception:
                pass

        self.simulation_app.set_setting("/app/livestream/enabled", True)
        self.simulation_app.set_setting("/app/livestream/proto", "webrtc")
        self.simulation_app.set_setting("/app/window/drawMouse", True)
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/streamType", "webrtc")
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/signalPort", signal_port)
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/streamPort", stream_port)
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/targetFps", int(settings.simulation.max_framerate))
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/publicIp", public_ip)
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/enableAudioCapture", False)
        self.simulation_app.set_setting("/app/livestream/webrtc/max_bitrate", int(settings.simulation.max_bitrate))
        self.simulation_app.set_setting("/app/livestream/webrtc/max_framerate", int(settings.simulation.max_framerate))
        self.simulation_app.set_setting("/app/livestream/webrtc/stream_width", int(settings.simulation.stream_resolution[0]))
        self.simulation_app.set_setting("/app/livestream/webrtc/stream_height", int(settings.simulation.stream_resolution[1]))
        self.simulation_app.set_setting("/app/livestream/webrtc/iceServers/0/urls", settings.simulation.stun_server)
        self.simulation_app.set_setting("/app/livestream/webrtc/dynamic_resize", True)
        self.simulation_app.set_setting("/exts/omni.kit.livestream.app/primaryStream/dynamicResize", True)
        self.simulation_app.set_setting("/app/window/width", int(settings.simulation.stream_resolution[0]))
        self.simulation_app.set_setting("/app/window/height", int(settings.simulation.stream_resolution[1]))
        self.simulation_app.set_setting("/app/window/fullscreen", False)
        self.simulation_app.set_setting("/app/window/enableHDPI", True)
        self.simulation_app.set_setting("/app/audio/enabled", False)

    def _initialize_world(self):
        try:
            scene_setup = SceneSetup()
            return scene_setup.initialize_world()
        except Exception as exc:
            logger.error("[AppCore] Не удалось инициализировать World: %s", exc)
            return None

    def run(self):
        logger.info("[AppCore] Запуск основного цикла симуляции. Нажмите Ctrl+C для выхода.")
        while self.simulation_app.is_running():
            if self.world is not None:
                self.world.step(render=True)
            else:
                self.simulation_app.update()

    def close(self):
        logger.warning("[AppCore] Закрытие SimulationApp...")
        self.simulation_app.close()
        try:
            os.chdir(self._prev_cwd)
        except Exception:
            pass
