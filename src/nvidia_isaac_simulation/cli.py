import argparse
import sys
from nvidia_isaac_simulation.utils import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="NVIDIA Isaac Sim Simulation App CLI")
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")
    
    start_sim_parser = subparsers.add_parser("start-sim", help="Запуск симуляции (согласно конфигу settings.toml)")
    # start_sim_parser.add_argument("--config", default="settings.toml", help="Путь к файлу конфигурации")
    args = parser.parse_args()
    
    if args.command == "start-sim":
        from nvidia_isaac_simulation.app import AppCore
        sim_app = None
        try:
            sim_app = AppCore()
            sim_app.run()
        except KeyboardInterrupt:
            logger.warning("\n[CLI] Остановка по Ctrl+C...")
        finally:
            if sim_app:
                sim_app.close()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
