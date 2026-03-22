import os
from pathlib import Path

os.environ["ACCEPT_EULA"] = "Y"

from nvidia_isaac_simulation.config import settings, PROJECT_ROOT
from nvidia_isaac_simulation.utils import get_logger
from isaacsim.simulation_app import SimulationApp

logger = get_logger(__name__)

class AppCore:
    def __init__(self):
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("CARB_LOGS", str(log_dir))
        os.environ.setdefault("OMNI_APP_LOG_DIR", str(log_dir))
        os.environ.setdefault("NV_STREAMER_LOG_DIR", str(log_dir))

        sim_config = {
            "headless": settings.simulation.headless,

        }
        self.simulation_app = SimulationApp(sim_config)
        self._setup_settings()
       
    def _setup_settings(self):
        signal_port = int(settings.WEBRTC__SIGNALER_PORT)
        stream_port = int(settings.WEBRTC__STREAMING_PORT)
        public_ip = str(settings.WEBRTC__PUBLIC_IP)

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

    def run(self):
        logger.info("[AppCore] Запуск основного цикла симуляции. Нажмите Ctrl+C для выхода.")
        while self.simulation_app.is_running():
            self.simulation_app.update()

    def close(self):
        logger.warning("[AppCore] Закрытие SimulationApp...")
        self.simulation_app.close()
