"""Service layer for CommunicationResult persistence and retrieval.

This service is the single entry point for:
  - Saving playground / pipeline analysis results to the database.
  - Querying and filtering results for a specific task run.
  - Generating aggregated statistics per task run.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from service.models.pydantic.communication import (
    CommunicationResultPage,
    CommunicationSummary,
    TaskCommunicationStats,
)
from service.repositories.base_repository import PaginationResult
from service.repositories.communication_result_repository import (
    CommunicationResultRepository,
)
from service.services.base_service import BaseService
from service.utils.logger import get_logger

logger = get_logger(__name__)


class CommunicationResultService(BaseService[CommunicationResultRepository]):
    """Service for managing communication classification results."""

    def __init__(self, repository: CommunicationResultRepository) -> None:
        super().__init__(repository)

    # ------------------------------------------------------------------ #
    # Write                                                                 #
    # ------------------------------------------------------------------ #

    async def save_playground_results(
        self,
        task_id: UUID,
        results: list[dict[str, Any]],
    ) -> int:
        """Persist results returned by ``PlaygroundService.process_batch``.

        The *results* list is the direct output of ``playground.evaluate_multiple_pushes_multiple_rules``.
        Each element is expected to have at least the following keys (but the
        service is lenient — missing keys default to safe values):

        - ``text`` / ``communication_text``  — source message text
        - ``type``                            — channel type (push / sms / email)
        - ``product_type``                   — financial product type
        - ``risk_ids_pred``                  — list of predicted risk IDs
        - ``risk_info``                      — dict with detailed risk information
        - ``triggers``                       — optional triggers dict
        - ``reasoning``                      — optional LLM reasoning text
        - ``model_used``                     — optional model name
        - ``processing_time_ms``             — optional int

        Args:
            task_id: ID of the associated Task record.
            results: List of analysis result dicts from PlaygroundService.

        Returns:
            Number of records saved.
        """
        if not results:
            logger.debug("save_playground_results: empty results for task %s, skipping", task_id)
            return 0

        items = []
        for r in results:
            items.append({
                "communication_text": (
                    r.get("text")
                    or r.get("communication_text")
                    or r.get("push_text")
                    or ""
                ),
                "communication_type": r.get("type") or r.get("communication_type") or "push",
                "product_type": r.get("product_type") or "all",
                "extra_metadata": r.get("extra_metadata") or r.get("metadata") or {},
                "risk_ids_pred": r.get("risk_ids_pred") or r.get("risks") or [],
                "risk_info": r.get("risk_info") or {},
                "triggers": r.get("triggers"),
                "reasoning": r.get("reasoning") or r.get("explanation"),
                "status": "completed",
                "processing_time_ms": r.get("processing_time_ms"),
                "model_used": r.get("model_used") or r.get("model"),
                "error_text": r.get("error_text") or r.get("error"),
                "rule_id": r.get("rule_id"),
            })

        try:
            saved = await self.repository.bulk_save_results(task_id=task_id, items=items)
            logger.info(
                "Saved %d playground results for task %s", len(saved), task_id
            )
            return len(saved)
        except Exception:
            logger.exception(
                "Failed to save playground results for task %s", task_id
            )
            return 0

    async def save_pipeline_results(
        self,
        task_id: UUID,
        result_context: dict[str, Any],
    ) -> int:
        """Persist results produced by ``PipelineService.process_pipe``.

        The pipeline returns a context dict that may contain a ``results`` or
        ``predictions`` key with per-communication analysis dicts.  If the
        pipeline did not produce per-communication data (e.g. it only generated
        report files), we save a single summary record so the task is at least
        represented in the results table.

        Args:
            task_id: ID of the associated Task record.
            result_context: The dict returned by ``PipelineService.process_pipe``.

        Returns:
            Number of records saved.
        """
        if not result_context:
            return 0

        # Try to extract per-communication results from context
        communications_data: list[dict] = (
            result_context.get("results")
            or result_context.get("predictions")
            or result_context.get("communications")
            or []
        )

        if communications_data:
            return await self.save_playground_results(task_id, communications_data)

        # No per-communication data — save a pipeline-level summary record
        try:
            await self.repository.save_communication_result(
                task_id=task_id,
                communication_text="[Pipeline run — see artifacts for per-row results]",
                communication_type="pipeline",
                product_type="all",
                risk_ids_pred=[],
                risk_info={"summary": result_context.get("metrics") or {}},
                status="completed",
            )
            logger.info("Saved pipeline summary record for task %s", task_id)
            return 1
        except Exception:
            logger.exception("Failed to save pipeline summary record for task %s", task_id)
            return 0

    # ------------------------------------------------------------------ #
    # Read                                                                  #
    # ------------------------------------------------------------------ #

    async def list_results(
        self,
        task_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        risk_id_filter: str | None = None,
        status_filter: str | None = None,
        type_filter: str | None = None,
        product_type_filter: str | None = None,
        has_risks: bool | None = None,
    ) -> CommunicationResultPage:
        """Return a paginated, filterable list of results for a task.

        See ``CommunicationResultRepository.list_results_for_task`` for full
        filter documentation.

        Returns:
            ``CommunicationResultPage`` with pydantic-serialised items.
        """
        page_size = max(1, min(page_size, 200))
        page = max(1, page)

        pagination: PaginationResult = await self.repository.list_results_for_task(
            task_id=task_id,
            page=page,
            page_size=page_size,
            search=search,
            risk_id_filter=risk_id_filter,
            status_filter=status_filter,
            type_filter=type_filter,
            product_type_filter=product_type_filter,
            has_risks=has_risks,
        )

        # Build summary items from ORM objects
        items: list[CommunicationSummary] = []
        for comm in pagination.items:
            # Aggregate risk_ids_pred across all results
            all_risk_ids: list[str] = []
            for result in (comm.results or []):
                all_risk_ids.extend(result.risk_ids_pred or [])
            unique_risk_ids = sorted(set(all_risk_ids))

            items.append(
                CommunicationSummary(
                    id=comm.id,
                    communication_id=comm.communication_id,
                    task_id=comm.task_id,
                    text=comm.text,
                    type=comm.type,
                    product_type=comm.product_type,
                    created_at=comm.created_at,
                    processed_at=comm.processed_at,
                    risk_ids_pred=unique_risk_ids,
                    result_count=len(comm.results or []),
                    has_risks=bool(unique_risk_ids),
                )
            )

        return CommunicationResultPage(
            task_id=task_id,
            items=items,
            total=pagination.total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=pagination.total_pages,
            has_next=pagination.has_next,
            has_prev=pagination.has_prev,
        )

    async def get_task_stats(self, task_id: UUID) -> TaskCommunicationStats:
        """Return aggregated statistics for all communications of a task.

        Returns:
            ``TaskCommunicationStats`` pydantic model.
        """
        raw = await self.repository.get_task_stats(task_id)
        return TaskCommunicationStats(**raw)

    async def get_communication_detail(self, communication_id: UUID):
        """Return a single Communication with all its results eagerly loaded."""
        return await self.repository.get_communication_with_results(communication_id)

    async def count_results(self, task_id: UUID) -> int:
        """Return the count of saved results for a task (used for health checks)."""
        return await self.repository.count_results_for_task(task_id)
