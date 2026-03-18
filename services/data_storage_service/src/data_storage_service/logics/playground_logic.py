"""Playground logic - business layer for communication analysis.

Handles single and batch communication processing through Playground.
Uses TaskOrchestratorService for task management.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from service.logics.base_logic import BaseLogic
from service.models.enums import TaskStatus, TaskType
from service.services.task_orchestrator_service import TaskOrchestratorService


class PlaygroundLogic(BaseLogic):
    """Business logic for playground (single/batch communication analysis).
    
    This logic layer:
    1. Validates input data
    2. Handles file config upload if provided
    3. Creates tasks via TaskOrchestratorService
    4. Returns task info for tracking
    """

    async def analyze_communications(
        self,
        communications: list[dict[str, Any]],
        config: dict[str, Any] | None = None,
        config_file_id: UUID | None = None,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Analyze communications (single or batch).
        
        Args:
            communications: List of communication dicts with:
                - text: message text
                - type: communication type (push, sms, etc.)
            config: Optional configuration dict with:
                - batch_size: items per batch (default: 10)
                - max_parallel_batches: threads to use (default: 3)
                - include_risk_ids: optional risk filter
            config_file_id: Optional uploaded config file ID
            user_id: User ID if authenticated
            guest_session_id: Guest session ID if guest
            
        Returns:
            Dict with:
                - task_id: created task ID
                - task_type: PLAYGROUND_SINGLE or PLAYGROUND_BATCH
                - status: pending or processing
                - threads_requested: number of threads requested
        """
        # Validate input
        if not communications:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one communication is required"
            )
        
        if not user_id and not guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication required"
            )
        
        # Validate communications structure
        for i, comm in enumerate(communications):
            if not comm.get("text"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Communication {i} missing required 'text' field"
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
        merged_config = self._merge_config(config, config_path, rules_list)
        
        # Determine task type
        task_type = (
            TaskType.PLAYGROUND_SINGLE
            if len(communications) == 1
            else TaskType.PLAYGROUND_BATCH
        )
        
        # Create task via orchestrator
        orchestrator = self.container.task_orchestrator_service()
        
        task = await orchestrator.create_playground_task(
            communications=communications,
            config=merged_config,
            user_id=user_id,
            guest_session_id=guest_session_id,
        )
        
        return {
            "task_id": task.id,
            "task_type": task_type.value,
            "status": task.status,
            "threads_requested": merged_config.get("max_parallel_batches", 1),
            "communications_count": len(communications),
        }
    
    async def get_task_status(self, task_id: UUID) -> dict[str, Any] | None:
        """Get status of a playground task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status info or None if not found
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)
        
        if not task:
            return None
        
        result = task.result or {}
        
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "progress": result.get("progress") if task.status == TaskStatus.PROCESSING.value else None,
            "error_message": task.error_message,
        }
    
    async def get_results(self, task_id: UUID, user_id: UUID | None = None, guest_session_id: UUID | None = None) -> dict[str, Any] | None:
        """Get analysis results for a completed task.
        
        Args:
            task_id: Task ID
            user_id: User ID for verification
            guest_session_id: Guest session ID for verification
            
        Returns:
            Results dict or None if not found/not completed
        """
        orchestrator = self.container.task_orchestrator_service()
        task = await orchestrator.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        # Verify ownership
        if task.user_id != user_id and task.guest_session_id != guest_session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this task"
            )
        
        if task.status != TaskStatus.COMPLETED.value:
            return {
                "task_id": task.id,
                "status": task.status,
                "message": "Task not yet completed",
                "results": None,
            }
        
        return {
            "task_id": task.id,
            "status": task.status,
            "results": task.result,
        }
    
    async def list_user_tasks(
        self,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List playground tasks for a user.
        
        Args:
            user_id: User ID
            guest_session_id: Guest session ID
            status: Optional status filter
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of task summaries
        """
        orchestrator = self.container.task_orchestrator_service()
        
        tasks = await orchestrator.get_user_tasks(
            user_id=user_id,
            guest_session_id=guest_session_id,
            task_type=None,  # All playground types
            status=status,
            limit=limit,
            offset=offset,
        )
        
        return [
            {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message,
                "config": task.config,
                "payload": task.payload,
                "result": task.result,
                "communications_count": len(task.payload.get("communications", [])),
            }
            for task in tasks
            if task.task_type in (TaskType.PLAYGROUND_SINGLE.value, TaskType.PLAYGROUND_BATCH.value)
        ]
    
    async def cancel_task(
        self,
        task_id: UUID,
        user_id: UUID | None = None,
        guest_session_id: UUID | None = None,
    ) -> bool:
        """Cancel a pending or processing task.
        
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
                detail="Not authorized to cancel this task"
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
    ) -> dict[str, Any]:
        """Merge inline config with file config and rules snapshot.
        
        Args:
            config: Inline config dict
            config_path: Resolved path to config file (or None)
            rules_list: Serialised list of rule dicts for RuleConfig
            
        Returns:
            Merged config
        """
        merged = dict(config or {})

        if config_path:
            merged["config_path"] = config_path

        if rules_list is not None:
            merged["rules"] = rules_list

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
