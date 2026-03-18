"""Worker manager for orchestrating multiple Celery workers.

Provides:
- Start/Stop/Restart workers
- Health monitoring
- Worker statistics tracking
- Dynamic thread allocation support

Thread allocation is managed by TaskOrchestratorService, not by workers directly.
Workers provide capacity while TaskOrchestratorService controls per-task thread usage.
"""

import logging
import subprocess
import sys
import time
from typing import Dict, List, Optional

from service.infrastructure.messaging.workers.maintenance_worker import MaintenanceWorker
from service.infrastructure.messaging.workers.pipeline_worker import PipelineWorker
from service.infrastructure.messaging.workers.playground_worker import PlaygroundWorker

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages lifecycle and health of Celery workers.

    Supports:
    - Multiple worker types (playground, pipeline, maintenance)
    - Dynamic thread allocation (controlled by TaskOrchestratorService)
    - Process-based worker management
    - Health monitoring
    
    Note: Actual thread usage per task is controlled by TaskOrchestratorService
    via max_parallel_batches from task config, not by worker settings.
    """

    def __init__(self, celery_app=None):
        self.celery_app = celery_app
        self.workers: Dict[str, subprocess.Popen] = {}
        self.worker_configs = {
            "playground": PlaygroundWorker,
            "pipeline": PipelineWorker,
            "maintenance": MaintenanceWorker,
        }
        logger.info("WorkerManager initialized with dynamic thread allocation support")

    def start_worker(
        self,
        worker_type: str,
        worker_name: Optional[str] = None,
        concurrency: Optional[int] = None,
    ) -> bool:
        """Start a worker of specified type.
        
        Args:
            worker_type: Type of worker (playground, pipeline, maintenance)
            worker_name: Optional custom worker name
            concurrency: Optional override for max concurrent tasks
            
        Returns:
            True if started successfully
        """
        if worker_type not in self.worker_configs:
            logger.error(f"Unknown worker type: {worker_type}")
            return False
        
        worker_name = worker_name or f"{worker_type}_worker_{int(time.time())}"
        
        if worker_name in self.workers:
            logger.warning(f"Worker {worker_name} already running")
            return False
        
        worker_class = self.worker_configs[worker_type]
        worker = worker_class(self.celery_app)

        # Use provided concurrency or worker default
        # Note: This is max concurrent tasks, not thread allocation
        actual_concurrency = concurrency or worker.concurrency

        try:
            cmd = [
                "celery",
                "-A",
                "service.infrastructure.messaging.app.celery_app",
                "worker",
                f"--queues={worker.queue}",
                f"--concurrency={actual_concurrency}",
                f"--prefetch-multiplier={worker.prefetch_multiplier}",
                f"--max-tasks-per-child={worker.max_tasks_per_child}",
                f"--time-limit={worker.time_limit}",
                f"--soft-time-limit={worker.soft_time_limit}",
                f"--hostname={worker_name}@%h",
                "--loglevel=INFO",
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.workers[worker_name] = process
            logger.info(
                f"Started worker {worker_name} (PID: {process.pid}, "
                f"type={worker_type}, queue={worker.queue}, "
                f"max_tasks={actual_concurrency})"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to start worker {worker_name}: {e}")
            return False

    def stop_worker(self, worker_name: str, timeout: int = 30) -> bool:
        """Stop a specific worker.
        
        Args:
            worker_name: Name of the worker to stop
            timeout: Seconds to wait for graceful shutdown
            
        Returns:
            True if stopped successfully
        """
        if worker_name not in self.workers:
            logger.warning(f"Worker {worker_name} not found")
            return False

        process = self.workers[worker_name]

        try:
            logger.info(f"Stopping worker {worker_name} (PID: {process.pid})...")
            process.terminate()

            try:
                process.wait(timeout=timeout)
                logger.info(f"Worker {worker_name} stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Worker {worker_name} did not stop gracefully, killing..."
                )
                process.kill()
                process.wait()

            del self.workers[worker_name]
            return True

        except Exception as e:
            logger.exception(f"Failed to stop worker {worker_name}: {e}")
            return False

    def restart_worker(self, worker_name: str, timeout: int = 30) -> bool:
        """Restart a specific worker."""
        if worker_name not in self.workers:
            logger.warning(f"Worker {worker_name} not found")
            return False

        worker_type = worker_name.split("_")[0]

        if self.stop_worker(worker_name, timeout):
            time.sleep(2)  # Brief pause before restart
            return self.start_worker(worker_type, worker_name)

        return False

    def stop_all_workers(self, timeout: int = 30):
        """Stop all running workers."""
        logger.info(f"Stopping all {len(self.workers)} workers...")
        worker_names = list(self.workers.keys())

        for worker_name in worker_names:
            self.stop_worker(worker_name, timeout)

        logger.info("All workers stopped")

    def get_worker_health(self, worker_name: str) -> Optional[Dict]:
        """Get health status of a specific worker."""
        if worker_name not in self.workers:
            return None

        process = self.workers[worker_name]
        return {
            "name": worker_name,
            "pid": process.pid,
            "running": process.poll() is None,
            "returncode": process.returncode,
        }

    def get_all_workers_health(self) -> List[Dict]:
        """Get health status of all workers."""
        return [
            self.get_worker_health(name)
            for name in self.workers.keys()
            if self.get_worker_health(name)
        ]

    def start_all_workers(self) -> Dict[str, bool]:
        """Start one instance of each worker type."""
        logger.info("Starting all workers with dynamic thread allocation...")
        results = {}
        
        for worker_type in self.worker_configs.keys():
            worker_name = f"{worker_type}_worker_default"
            success = self.start_worker(worker_type, worker_name)
            results[worker_type] = success
        
        total = sum(results.values())
        logger.info(f"Started {total}/{len(results)} workers")
        return results

    def start_production_workers(
        self,
        playground_count: int = 2,
        pipeline_count: int = 1,
        maintenance_count: int = 2,
    ) -> Dict[str, List[str]]:
        """Start production worker configuration.

        Args:
            playground_count: Number of playground workers
            pipeline_count: Number of pipeline workers
            maintenance_count: Number of maintenance workers
            
        Returns:
            Dict mapping worker type to list of started worker names
            
        Note: Each task's actual thread usage is controlled by
        TaskOrchestratorService based on max_parallel_batches config.
        """
        logger.info(
            f"Starting production workers: "
            f"playground={playground_count}, pipeline={pipeline_count}, "
            f"maintenance={maintenance_count}"
        )
        worker_names: Dict[str, List[str]] = {}

        # Start playground workers
        worker_names["playground"] = []
        for i in range(playground_count):
            name = f"playground_worker_{i+1}"
            if self.start_worker("playground", name):
                worker_names["playground"].append(name)

        # Start pipeline workers
        worker_names["pipeline"] = []
        for i in range(pipeline_count):
            name = f"pipeline_worker_{i+1}"
            if self.start_worker("pipeline", name):
                worker_names["pipeline"].append(name)

        # Start maintenance workers
        worker_names["maintenance"] = []
        for i in range(maintenance_count):
            name = f"maintenance_worker_{i+1}"
            if self.start_worker("maintenance", name):
                worker_names["maintenance"].append(name)

        total = sum(len(names) for names in worker_names.values())
        logger.info(f"Production workers started: {total} total")

        return worker_names


# CLI entry point for worker manager
def main():
    """CLI entry point for worker management."""
    if len(sys.argv) < 2:
        print("Usage: python -m service.infrastructure.messaging.workers.worker_manager <command> [args]")
        print("Commands:")
        print("  start <worker_type>         - Start single worker")
        print("  start-all                   - Start one instance of each worker type")
        print("  start-production [p] [pl] [m] - Start production config (default: 2 1 2)")
        print("  stop <worker_name>          - Stop specific worker")
        print("  stop-all                    - Stop all workers")
        print("  restart <worker_name>       - Restart specific worker")
        print("  status                      - Show all workers status")
        print("")
        print("Worker types: playground, pipeline, maintenance")
        print("")
        print("Note: Thread allocation is controlled by TaskOrchestratorService")
        print("      based on max_parallel_batches from task config.")
        sys.exit(1)

    from service.infrastructure.messaging.app.celery_app import celery_app

    manager = WorkerManager(celery_app)
    command = sys.argv[1]

    if command == "start":
        if len(sys.argv) < 3:
            print("Usage: start <worker_type>")
            print("Available types: playground, pipeline, maintenance")
            sys.exit(1)
        worker_type = sys.argv[2]
        success = manager.start_worker(worker_type)
        if success:
            print(f"✓ Started {worker_type} worker")
        else:
            print(f"✗ Failed to start {worker_type} worker")
            sys.exit(1)

    elif command == "start-all":
        results = manager.start_all_workers()
        for worker_type, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {worker_type} worker")

    elif command == "start-production":
        # Parse optional counts
        p = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        pl = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        m = int(sys.argv[4]) if len(sys.argv) > 4 else 2
        
        worker_names = manager.start_production_workers(p, pl, m)
        print("\nProduction workers started:")
        for worker_type, names in worker_names.items():
            print(f"  {worker_type}: {len(names)} workers - {', '.join(names)}")
        print(f"\nNote: Thread allocation controlled by TaskOrchestratorService")

    elif command == "stop":
        if len(sys.argv) < 3:
            print("Usage: stop <worker_name>")
            sys.exit(1)
        worker_name = sys.argv[2]
        success = manager.stop_worker(worker_name)
        if success:
            print(f"✓ Stopped {worker_name}")
        else:
            print(f"✗ Failed to stop {worker_name}")
            sys.exit(1)

    elif command == "stop-all":
        manager.stop_all_workers()
        print("✓ All workers stopped")

    elif command == "restart":
        if len(sys.argv) < 3:
            print("Usage: restart <worker_name>")
            sys.exit(1)
        worker_name = sys.argv[2]
        success = manager.restart_worker(worker_name)
        if success:
            print(f"✓ Restarted {worker_name}")
        else:
            print(f"✗ Failed to restart {worker_name}")
            sys.exit(1)

    elif command == "status":
        health = manager.get_all_workers_health()
        if not health:
            print("No workers running")
        else:
            print(f"\nWorker Status ({len(health)} workers):")
            print("-" * 60)
            for worker in health:
                status = "✓ Running" if worker["running"] else "✗ Stopped"
                print(
                    f"{worker['name']:<30} "
                    f"PID: {worker['pid']:<8} "
                    f"{status}"
                )
            print("-" * 60)
            print("\nNote: Thread allocation controlled by TaskOrchestratorService")

    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage")
        sys.exit(1)


if __name__ == "__main__":
    main()