"""Pipeline logic - business layer for dataset analysis.

Handles pipeline task creation and report management.
Uses TaskOrchestratorService for task management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from service.logics.base_logic import BaseLogic
from service.models.enums import TaskStatus, TaskType


class PipelineLogic(BaseLogic):
    """Business logic for pipeline (dataset analysis).
    
    This logic layer:
    1. Validates dataset file
    2. Creates pipeline tasks via TaskOrchestratorService
    3. Manages pipeline reports and artifacts
    4. Provides queue status for waiting tasks
    """

    async def run_pipeline(
        self,
        dataset_file_id: UUID,
        config: dict[str, Any] | None = None,
        config_file_id: UUID | None = None,
        format_file: str = "xlsx",
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Start a pipeline analysis on a dataset.
        
        Args:
            dataset_file_id: ID of uploaded XLSX dataset file
            config: Optional configuration dict with:
                - max_parallel_batches: threads for pipeline (default: 3)
                - include_risk_ids: optional risk filter
            config_file_id: Optional pipeline config file ID
            format_file: Dataset file format (default: xlsx)
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if guest
            
        Returns:
            Dict with:
                - task_id: created task ID
                - status: pending or processing
                - threads_requested: number of threads
        """
        # Validate input
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication required"
            )
        
        # Verify dataset file exists and validate type
        file_saver = self.container.file_saver_service()
        try:
            file_meta = await file_saver.fetch_file_metadata(
                dataset_file_id, user_id=user_id, guest_session_id=guest_session_id
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset file {dataset_file_id} not found",
            ) from exc

        if not file_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset file {dataset_file_id} not found",
            )

        # Validate file type
        if not file_meta.file_name.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset must be an Excel or CSV file"
            )

        # Fetch user rules snapshot (authenticated users only)
        rules_list = []
        if user_id:
            try:
                rule_svc = self.container.rule_service()
                snapshot = await rule_svc.get_user_rules_snapshot(user_id)
                rules_list = [entry.model_dump(mode="json") for entry in snapshot.rules]
            except Exception as e:
                self.logger.warning(f"Failed to fetch user rules snapshot: {e}")

        # Resolve config file path if provided
        config_path = None
        if config_file_id:
            config_path = await self._resolve_file_path(config_file_id)

        # Prepare config
        merged_config = self._merge_config(config, config_path, rules_list, format_file)
        
        # Create task via orchestrator
        orchestrator = self.container.task_orchestrator_service()
        
        try:
            task = await orchestrator.create_pipeline_task(
                dataset_file_id=dataset_file_id,
                config=merged_config,
                user_id=user_id,
                guest_session_id=guest_session_id,
            )
        except Exception as e:
            self.logger.exception(f"Failed to create pipeline task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create pipeline task: {str(e)}"
            )
        
        return {
            "task_id": task.id,
            "task_type": TaskType.PIPELINE.value,
            "status": task.status,
            "threads_requested": merged_config.get("max_parallel_batches", 1),
            "dataset_file": file_meta.file_name,
        }
    
    async def get_task_status(self, task_id: UUID) -> dict[str, Any] | None:
        """Get status of a pipeline task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status info or None if not found
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)
        
        if not task:
            return None
        
        # Get queue position if pending
        queue_position = None
        if task.status == TaskStatus.PENDING.value:
            queue_info = await orchestrator.get_pipeline_queue_position(
                task_id=task_id,
                user_id=task.user_id,
                guest_session_id=task.guest_session_id,
            )
            queue_position = queue_info.get("position")
        
        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "queue_position": queue_position,
            "threads_requested": task.config.get("max_parallel_batches", 1) if task.config else 1,
            "error_message": task.error_message,
        }
    
    async def get_pipeline_reports(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get history of pipeline runs with reports.
        
        Args:
            user_id: User ID
            guest_session_id: Guest session ID
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of pipeline report summaries
        """
        orchestrator = self.container.task_orchestrator_service()
        
        tasks = await orchestrator.get_user_tasks(
            user_id=user_id,
            guest_session_id=guest_session_id,
            task_type=TaskType.PIPELINE,
            status=None,
            limit=limit,
            offset=offset,
        )
        
        reports = []
        for task in tasks:
            # Get dataset file name for display
            file_saver = self.container.file_saver_service()
            dataset_name = "Unknown"
            if task.file_id:
                try:
                    file_meta = await file_saver.fetch_file_metadata(task.file_id)
                    dataset_name = file_meta.file_name
                except Exception:
                    pass
            
            # Count artifacts
            artifact_count = len(task.artifact_paths) if task.artifact_paths else 0
            
            # Get metrics from result
            result = task.result or {}
            metrics = result.get("metrics", {})
            
            reports.append({
                "task_id": task.id,
                "status": task.status,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "dataset_name": dataset_name,
                "threads_used": task.config.get("max_parallel_batches", 1) if task.config else 1,
                "artifact_count": artifact_count,
                "artifact_paths": task.artifact_paths or [],
                "metrics": {
                    "rows_processed": metrics.get("rows_processed"),
                    "risks_detected": metrics.get("risks_detected"),
                    "avg_confidence": metrics.get("avg_confidence"),
                } if metrics else None,
            })
        
        return reports
    
    async def get_report_details(
        self,
        task_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get detailed report for a completed pipeline.
        
        Args:
            task_id: Pipeline task ID
            user_id: User ID for verification
            guest_session_id: Guest session ID for verification
            
        Returns:
            Detailed report with artifact links
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Verify ownership
        if task.user_id != user_id and task.guest_session_id != guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this report"
            )
        
        if task.task_type != TaskType.PIPELINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not a pipeline task"
            )
        
        # Get dataset file name for display
        file_saver = self.container.file_saver_service()
        dataset_name = "Unknown"
        if task.file_id:
            try:
                file_meta = await file_saver.fetch_file_metadata(task.file_id)
                dataset_name = file_meta.file_name
            except Exception:
                pass
        
        # Get artifacts
        artifacts = []
        if task.artifact_paths:
            for path in task.artifact_paths:
                path_obj = Path(path)
                artifacts.append({
                    "name": path_obj.name,
                    "path": path,
                    "type": path_obj.suffix.lstrip("."),
                    "size": path_obj.stat().st_size if path_obj.exists() else None,
                })
        
        result = task.result or {}
        
        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "dataset_name": dataset_name,
            "threads_used": task.config.get("max_parallel_batches", 1) if task.config else 1,
            "artifacts": artifacts,
            "metrics": result.get("metrics", {}),
            "results": result,
        }
    
    async def download_artifact(
        self,
        task_id: UUID,
        artifact_path: str,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> bytes:
        """Download an artifact file.
        
        Args:
            task_id: Pipeline task ID
            artifact_path: Path to artifact
            user_id: User ID for verification
            guest_session_id: Guest session ID for verification
            
        Returns:
            File bytes
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Verify ownership
        if task.user_id != user_id and task.guest_session_id != guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        
        # Verify artifact belongs to task
        if not task.artifact_paths or artifact_path not in task.artifact_paths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found"
            )
        
        path_obj = Path(artifact_path)
        if not path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact file not found"
            )
        
        return path_obj.read_bytes()
    
    async def cancel_task(
        self,
        task_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> bool:
        """Cancel a pending pipeline task.
        
        Args:
            task_id: Task ID
            user_id: User ID for verification
            guest_session_id: Guest session ID for verification
            
        Returns:
            True if cancelled
        """
        orchestrator = self.container.task_orchestrator_service()
        
        # Verify ownership
        task = await orchestrator.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.user_id != user_id and task.guest_session_id != guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized"
            )
        
        if task.task_type != TaskType.PIPELINE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not a pipeline task"
            )
        
        if task.status not in (TaskStatus.PENDING.value, TaskStatus.PROCESSING.value, TaskStatus.NEW.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task in status {task.status}"
            )
        
        return await orchestrator.cancel_task(task_id)
    
    def _merge_config(
        self,
        config: dict[str, Any] | None,
        config_path: str | None,
        rules_list: list[dict] | None,
        format_file: str = "xlsx",
    ) -> dict[str, Any]:
        """Merge inline config with file config, rules snapshot and format.
        
        Args:
            config: Inline config dict
            config_path: Resolved path to config file (or None)
            rules_list: Serialised list of rule dicts for RuleConfig
            format_file: Dataset file format
            
        Returns:
            Merged config
        """
        merged = dict(config or {})

        if config_path:
            merged["config_path"] = config_path

        if rules_list is not None:
            merged["rules"] = rules_list

        merged.setdefault("format_file", format_file)

        return merged

    async def _resolve_file_path(self, file_id: UUID) -> str | None:
        """Resolve a file UUID to an access path / presigned URL.

        Delegates to ``FileSaverService.get_access_path`` so that the result is
        always correct for the configured storage backend (local path for local
        storage, time-limited presigned URL for MinIO / S3).

        Args:
            file_id: File record UUID

        Returns:
            Filesystem path or presigned URL, or ``None`` if file not found.
        """
        try:
            return await self.container.file_saver_service().get_access_path(file_id)
        except Exception as e:
            self.logger.warning(f"Failed to resolve file path for {file_id}: {e}")
        return None
