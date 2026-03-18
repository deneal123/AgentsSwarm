"""Tasks for file processing - config and dataset uploads.

Validates and processes uploaded configuration and dataset files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import yaml
from celery import shared_task

from service.infrastructure.messaging.tasks.base_task import PushiBaseTask
from service.models.enums import TaskStatus
from service.utils.logger import get_logger

if TYPE_CHECKING:
    from service.models.db.task_models import Task

logger = get_logger(__name__)


# ============================================================================
# Celery Task Functions
# ============================================================================

@shared_task(bind=True, base=PushiBaseTask, max_retries=2)
def process_config_upload(self, task_id: str) -> dict:
    """Process uploaded config file (.yaml, .toml).
    
    Celery task entry point.
    
    Args:
        task_id: Task UUID as string
        
    Returns:
        Processing result dict with validation results
    """
    processor = FileTaskProcessor()
    return processor.process_config(task_id)


@shared_task(bind=True, base=PushiBaseTask, max_retries=2)
def process_dataset_upload(self, task_id: str) -> dict:
    """Process uploaded dataset file (.xlsx).
    
    Celery task entry point.
    
    Args:
        task_id: Task UUID as string
        
    Returns:
        Processing result dict with dataset info
    """
    processor = FileTaskProcessor()
    return processor.process_dataset(task_id)


@shared_task(bind=True, base=PushiBaseTask, max_retries=2)
def process_rule_config(self, risk_id: str, toml_content: str) -> dict:
    """Process uploaded rules.toml file for risk.
    
    Celery task entry point for rule configuration updates.
    
    Args:
        risk_id: Risk UUID as string
        toml_content: TOML file content as string
        
    Returns:
        Processing result dict with rule creation results
    """
    processor = FileTaskProcessor()
    return processor.process_rule_config(risk_id, toml_content)
    

# ============================================================================
# Task Processor
# ============================================================================

class FileTaskProcessor:
    """Processor for file upload tasks. Validates and processes configs and datasets."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._task_repo = None
        self._file_repo = None

    def _run_async(self, coro):
        """Run a coroutine in a fresh, isolated event loop.

        Each Celery task invocation gets its own loop so that asyncpg
        connections (which are loop-bound) are never shared across loops.
        """
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    def process_config(self, task_id: str) -> dict:
        """Process and validate config file.
        
        Args:
            task_id: Task UUID string
            
        Returns:
            Result dict with:
                - status: completed/failed
                - validation_errors: list of validation errors if any
                - config_summary: summary of loaded config
        """
        return self._run_async(self._process_config_async(task_id))
    
    async def _process_config_async(self, task_id: str) -> dict:
        """Async implementation for config processing."""
        task_uuid = UUID(task_id)
        self.logger.info(f"Processing config upload: {task_id}")
        
        try:
            # Get repositories
            task_repo, file_repo = self._get_repositories()
            
            # Load task
            task = await task_repo.get_task_by_id(task_uuid)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if not task.file_id:
                raise ValueError("No file associated with task")
            
            # Load file record
            file_record = await file_repo.get_file_by_id(task.file_id)
            if not file_record:
                raise ValueError(f"File {task.file_id} not found")
            
            # Read and parse config
            file_path = self._resolve_storage_path(file_record.storage_path)
            if not file_path.exists():
                raise ValueError(f"Config file not found at {file_path}")
            
            config_data, validation_errors = await self._parse_config(file_path)
            
            # Update task with results
            status = "completed" if not validation_errors else "completed_with_warnings"
            
            await task_repo.update_task_fields(
                task_id=task_uuid,
                status=TaskStatus.COMPLETED,
                result={
                    "status": status,
                    "file_name": file_record.file_name,
                    "config_data": config_data,
                    "validation_errors": validation_errors,
                },
            )
            
            self.logger.info(
                f"Config processing completed: {task_id}, "
                f"errors={len(validation_errors)}"
            )
            
            return {
                "status": status,
                "task_id": task_id,
                "validation_errors": validation_errors,
                "config_summary": self._summarize_config(config_data),
            }
            
        except Exception as e:
            self.logger.exception(f"Config processing failed: {e}")
            try:
                task_repo, _ = self._get_repositories()
                await task_repo.update_task_fields(
                    task_id=task_uuid,
                    status=TaskStatus.FAILED,
                    result={"error": str(e)},
                )
            except Exception:
                pass
            raise
    
    def process_dataset(self, task_id: str) -> dict:
        """Process and validate dataset file.
        
        Args:
            task_id: Task UUID string
            
        Returns:
            Result dict with:
                - status: completed/failed
                - row_count: number of rows in dataset
                - column_info: info about columns
                - validation_errors: list of validation errors if any
        """
        return self._run_async(self._process_dataset_async(task_id))
    
    async def _process_dataset_async(self, task_id: str) -> dict:
        """Async implementation for dataset processing."""
        task_uuid = UUID(task_id)
        self.logger.info(f"Processing dataset upload: {task_id}")
        
        try:
            # Get repositories
            task_repo, file_repo = self._get_repositories()
            
            # Load task
            task = await task_repo.get_task_by_id(task_uuid)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if not task.file_id:
                raise ValueError("No file associated with task")
            
            # Load file record
            file_record = await file_repo.get_file_by_id(task.file_id)
            if not file_record:
                raise ValueError(f"File {task.file_id} not found")
            
            # Read and validate dataset
            file_path = self._resolve_storage_path(file_record.storage_path)
            if not file_path.exists():
                raise ValueError(f"Dataset file not found at {file_path}")
            
            dataset_info, validation_errors = await self._parse_dataset(file_path)
            
            # Update task with results
            status = "completed" if not validation_errors else "completed_with_warnings"
            
            await task_repo.update_task_fields(
                task_id=task_uuid,
                status=TaskStatus.COMPLETED,
                result={
                    "status": status,
                    "file_name": file_record.file_name,
                    "dataset_info": dataset_info,
                    "validation_errors": validation_errors,
                },
            )
            
            self.logger.info(
                f"Dataset processing completed: {task_id}, "
                f"rows={dataset_info.get('row_count', 0)}, "
                f"errors={len(validation_errors)}"
            )
            
            return {
                "status": status,
                "task_id": task_id,
                "row_count": dataset_info.get("row_count", 0),
                "column_info": dataset_info.get("columns", {}),
                "validation_errors": validation_errors,
            }
            
        except Exception as e:
            self.logger.exception(f"Dataset processing failed: {e}")
            try:
                task_repo, _ = self._get_repositories()
                await task_repo.update_task_fields(
                    task_id=task_uuid,
                    status=TaskStatus.FAILED,
                    result={"error": str(e)},
                )
            except Exception:
                pass
            raise
    
    def process_rule_config(self, risk_id: str, toml_content: str) -> dict:
        """Process and validate rules.toml file.
        
        Args:
            risk_id: Risk UUID as string
            toml_content: TOML file content as string
            
        Returns:
            Result dict with:
                - status: completed/failed
                - rules_created: number of rules created
                - validation_errors: list of validation errors if any
        """
        return self._run_async(self._process_rule_config_async(risk_id, toml_content))
    
    async def _process_rule_config_async(self, risk_id: str, toml_content: str) -> dict:
        """Async implementation for rule config processing."""
        risk_uuid = UUID(risk_id)
        self.logger.info(f"Processing rule config for risk: {risk_id}")
        
        try:
            # Get repositories
            task_repo, _ = self._get_repositories()
            
            # Parse TOML
            config, validation_errors = self._parse_toml_string(toml_content)
            
            if validation_errors:
                self.logger.warning(f"Rule config validation errors: {validation_errors}")
            
            # Create rules from config
            rules_created = 0
            for rule_def in config.get("rules", []):
                try:
                    # Here you would create the rule using RuleService
                    # For now, just log and count
                    rules_created += 1
                except Exception as e:
                    self.logger.error(f"Failed to create rule: {e}")
                    validation_errors.append(f"Rule creation failed: {e}")
            
            status = "completed" if not validation_errors else "completed_with_warnings"
            
            self.logger.info(
                f"Rule config processing completed: {risk_id}, "
                f"rules_created={rules_created}, "
                f"errors={len(validation_errors)}"
            )
            
            return {
                "status": status,
                "risk_id": risk_id,
                "rules_created": rules_created,
                "validation_errors": validation_errors,
            }
            
        except Exception as e:
            self.logger.exception(f"Rule config processing failed: {e}")
            raise
    
    def _parse_toml_string(self, toml_content: str) -> tuple[dict, list[str]]:
        """Parse TOML string.
        
        Args:
            toml_content: TOML content as string
            
        Returns:
            Tuple of (config, validation_errors)
        """
        errors = []
        config = {}
        
        try:
            import toml
            config = toml.loads(toml_content)
        except ImportError:
            errors.append("toml library not installed")
        except Exception as e:
            errors.append(f"TOML parsing error: {e}")
        
        return config, errors
    
    async def _parse_config(self, file_path: Path) -> tuple[dict, list[str]]:
        """Parse and validate config file.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Tuple of (config_data, validation_errors)
        """
        errors = []
        config_data = {}
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            if file_path.suffix in (".yaml", ".yml"):
                config_data = yaml.safe_load(content)
            elif file_path.suffix == ".toml":
                try:
                    import toml
                    config_data = toml.loads(content)
                except ImportError:
                    errors.append("toml library not installed, cannot parse .toml files")
                    return config_data, errors
            elif file_path.suffix == ".json":
                config_data = json.loads(content)
            else:
                errors.append(f"Unsupported config format: {file_path.suffix}")
                return config_data, errors
            
            # Validate config structure
            errors.extend(self._validate_config_structure(config_data))
            
        except yaml.YAMLError as e:
            errors.append(f"YAML parsing error: {e}")
        except json.JSONDecodeError as e:
            errors.append(f"JSON parsing error: {e}")
        except Exception as e:
            errors.append(f"Config parsing error: {e}")
        
        return config_data, errors
    
    def _validate_config_structure(self, config: dict) -> list[str]:
        """Validate config structure.
        
        Args:
            config: Parsed config dict
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Config must be a dictionary/object")
            return errors
        
        # Check required/optional fields
        known_fields = {
            "batch_size", "max_parallel_batches", "include_risk_ids",
            "llm_provider", "timeout", "retry_policy", "output_format",
        }
        
        for key in config.keys():
            if key not in known_fields:
                errors.append(f"Unknown config field: {key}")
        
        # Validate specific fields
        if "batch_size" in config:
            bs = config["batch_size"]
            if not isinstance(bs, int) or bs < 1 or bs > 1000:
                errors.append("batch_size must be an integer between 1 and 1000")
        
        if "max_parallel_batches" in config:
            mpb = config["max_parallel_batches"]
            if not isinstance(mpb, int) or mpb < 1 or mpb > 20:
                errors.append("max_parallel_batches must be an integer between 1 and 20")
        
        if "include_risk_ids" in config:
            risk_ids = config["include_risk_ids"]
            if not isinstance(risk_ids, list):
                errors.append("include_risk_ids must be a list")
        
        return errors
    
    async def _parse_dataset(self, file_path: Path) -> tuple[dict, list[str]]:
        """Parse and validate dataset file.
        
        Args:
            file_path: Path to dataset file
            
        Returns:
            Tuple of (dataset_info, validation_errors)
        """
        errors = []
        dataset_info = {}
        
        try:
            import pandas as pd
            
            # Read dataset
            if file_path.suffix == ".xlsx":
                df = pd.read_excel(file_path)
            elif file_path.suffix == ".csv":
                df = pd.read_csv(file_path)
            else:
                errors.append(f"Unsupported dataset format: {file_path.suffix}")
                return dataset_info, errors
            
            # Extract info
            dataset_info = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": {
                    col: {
                        "dtype": str(df[col].dtype),
                        "null_count": int(df[col].isnull().sum()),
                        "sample_values": df[col].dropna().head(3).tolist(),
                    }
                    for col in df.columns
                },
            }
            
            # Validate required columns for pipeline
            required_cols = {"text", "communication_type"}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                errors.append(f"Missing required columns: {missing_cols}")
            
            # Validate data quality
            if len(df) == 0:
                errors.append("Dataset is empty")
            elif len(df) > 100000:
                errors.append(f"Dataset too large: {len(df)} rows (max 100,000)")
            
            # Check for empty text cells
            if "text" in df.columns:
                empty_text = df["text"].isnull().sum() + (df["text"] == "").sum()
                if empty_text > 0:
                    errors.append(f"Found {empty_text} rows with empty text")
            
        except Exception as e:
            errors.append(f"Dataset parsing error: {e}")
        
        return dataset_info, errors
    
    def _summarize_config(self, config: dict) -> dict:
        """Create a summary of config for display.
        
        Args:
            config: Config dict
            
        Returns:
            Summary dict
        """
        return {
            "batch_size": config.get("batch_size", "default"),
            "max_parallel_batches": config.get("max_parallel_batches", "default"),
            "risk_filter": "enabled" if config.get("include_risk_ids") else "disabled",
            "llm_provider": config.get("llm_provider", "default"),
        }
    
    def _get_repositories(self):
        """Create fresh repositories bound to the current event loop.

        Each Celery task runs in its own event loop (created by _run_async).
        We must create a brand-new PgConnector with force_new=True so the
        SQLAlchemy async engine and asyncpg connection pool are tied to that
        loop — not to some older loop cached on the class.
        """
        if self._task_repo is None:
            from service.infrastructure.database.postgresql import PgConnector
            from service.repositories.file_repository import FileRepository
            from service.repositories.task_repository import TaskRepository
            from service.settings import Config

            connector = PgConnector(Config().pg, force_new=True)
            self._task_repo = TaskRepository(connector)
            self._file_repo = FileRepository(connector)
        return self._task_repo, self._file_repo

    @staticmethod
    def _resolve_storage_path(storage_path: str) -> Path:
        """Resolve a (possibly relative) storage_path to an absolute Path.

        The DB stores paths relative to StorageConfig.root
        (e.g. ``uploads/config_yaml/foo.yaml``).
        If the path is already absolute it is returned as-is.
        """
        p = Path(storage_path)
        if p.is_absolute():
            return p
        from service.settings import Config
        base = Path(Config().storage.root)
        return base / p

