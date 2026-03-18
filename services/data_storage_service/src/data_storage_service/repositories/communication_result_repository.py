"""Repository for Communication and CommunicationResult persistence.

Responsibilities:
  - Bulk-save Communication + CommunicationResult rows produced by
    playground / pipeline workers.
  - Paginated search / filter over results per task run.
  - Aggregate statistics per task (risk counts, processing times, etc.).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from service.models.db.communication_models import Communication, CommunicationResult
from service.repositories.base_repository import BaseRepository, PaginationResult
from service.repositories.decorators.session_processor import connection
from service.utils.logger import get_logger

logger = get_logger(__name__)


class CommunicationResultRepository(BaseRepository):
    """Repository for communication classification results."""

    # ------------------------------------------------------------------ #
    # Write                                                                 #
    # ------------------------------------------------------------------ #

    @connection()
    async def save_communication_result(
        self,
        *,
        task_id: UUID,
        communication_text: str,
        communication_type: str = "push",
        product_type: str = "all",
        extra_metadata: dict[str, Any] | None = None,
        risk_ids_pred: list[str] | None = None,
        risk_info: dict[str, Any] | None = None,
        triggers: dict[str, Any] | None = None,
        reasoning: str | None = None,
        status: str = "completed",
        processing_time_ms: int | None = None,
        model_used: str | None = None,
        error_text: str | None = None,
        rule_id: UUID | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[Communication, CommunicationResult]:
        """Persist a single communication and its classification result.

        Creates both a ``Communication`` record (the source text) and a
        ``CommunicationResult`` record (the analysis output) in one transaction.

        Returns:
            Tuple of (Communication, CommunicationResult).
        """
        assert session is not None

        now = datetime.now(timezone.utc)

        comm = Communication(
            id=uuid4(),
            communication_id=str(uuid4()),
            task_id=task_id,
            text=communication_text,
            ai=0,
            type=communication_type,
            product_type=product_type,
            extra_metadata=extra_metadata or {},
            created_at=now,
            processed_at=now,
        )
        session.add(comm)
        await session.flush()  # get comm.id

        result = CommunicationResult(
            id=uuid4(),
            communication_id=comm.id,
            task_id=task_id,
            rule_id=rule_id,
            risk_ids_pred=risk_ids_pred or [],
            risk_info=risk_info or {},
            triggers=triggers,
            reasoning=reasoning,
            status=status,
            processing_time_ms=processing_time_ms,
            model_used=model_used,
            error_text=error_text,
            extra_metadata={},
            created_at=now,
            finished_at=now,
        )
        session.add(result)
        await session.flush()

        logger.debug(
            "Saved communication %s result %s for task %s",
            comm.id,
            result.id,
            task_id,
        )
        return comm, result

    @connection()
    async def bulk_save_results(
        self,
        *,
        task_id: UUID,
        items: list[dict[str, Any]],
        session: AsyncSession | None = None,
    ) -> list[tuple[Communication, CommunicationResult]]:
        """Bulk-insert communications + results from a playground/pipeline run.

        Each item in *items* is a dict with keys matching
        ``CommunicationResultCreate`` fields.

        Returns:
            List of (Communication, CommunicationResult) tuples.
        """
        assert session is not None

        if not items:
            return []

        now = datetime.now(timezone.utc)
        saved: list[tuple[Communication, CommunicationResult]] = []

        for item in items:
            comm_id = uuid4()
            comm = Communication(
                id=comm_id,
                communication_id=str(uuid4()),
                task_id=task_id,
                text=item.get("communication_text", ""),
                ai=item.get("ai", 0),
                type=item.get("communication_type", "push"),
                product_type=item.get("product_type", "all"),
                extra_metadata=item.get("extra_metadata") or {},
                created_at=now,
                processed_at=now,
            )
            result = CommunicationResult(
                id=uuid4(),
                communication_id=comm_id,
                task_id=task_id,
                rule_id=item.get("rule_id"),
                risk_ids_pred=item.get("risk_ids_pred") or [],
                risk_info=item.get("risk_info") or {},
                triggers=item.get("triggers"),
                reasoning=item.get("reasoning"),
                status=item.get("status", "completed"),
                processing_time_ms=item.get("processing_time_ms"),
                model_used=item.get("model_used"),
                error_text=item.get("error_text"),
                extra_metadata={},
                created_at=now,
                finished_at=now,
            )
            session.add(comm)
            session.add(result)
            saved.append((comm, result))

        await session.flush()

        logger.info("Bulk-saved %d communication results for task %s", len(saved), task_id)
        return saved

    # ------------------------------------------------------------------ #
    # Read — paginated list with search/filter                             #
    # ------------------------------------------------------------------ #

    @connection()
    async def list_results_for_task(
        self,
        *,
        task_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        risk_id_filter: str | None = None,
        status_filter: str | None = None,
        type_filter: str | None = None,
        product_type_filter: str | None = None,
        has_risks: bool | None = None,
        session: AsyncSession | None = None,
    ) -> PaginationResult:
        """Return paginated Communication rows for a task, with optional filters.

        Joins Communication with CommunicationResult to expose aggregate
        risk_ids_pred for filtering.

        Args:
            task_id: The task whose communications to list.
            page: 1-based page number.
            page_size: Records per page.
            search: Full-text substring search over ``Communication.text``.
            risk_id_filter: Filter to communications that predict this risk_id.
            status_filter: Filter by CommunicationResult.status.
            type_filter: Filter by Communication.type (push/sms/email).
            product_type_filter: Filter by Communication.product_type.
            has_risks: If True — only comms with risk_ids_pred != [].
                       If False — only comms with empty risk_ids_pred.

        Returns:
            PaginationResult whose ``items`` are Communication ORM objects
            (with ``results`` relationship populated for each).
        """
        assert session is not None

        stmt = select(Communication).where(Communication.task_id == task_id)

        # Optional join to CommunicationResult for result-based filters
        need_join = (
            risk_id_filter is not None
            or status_filter is not None
            or has_risks is not None
        )
        if need_join:
            stmt = stmt.join(
                CommunicationResult,
                CommunicationResult.communication_id == Communication.id,
                isouter=True,
            )

        if search:
            stmt = stmt.where(Communication.text.ilike(f"%{search}%"))

        if type_filter:
            stmt = stmt.where(Communication.type == type_filter)

        if product_type_filter:
            stmt = stmt.where(Communication.product_type == product_type_filter)

        if risk_id_filter:
            stmt = stmt.where(
                CommunicationResult.risk_ids_pred.any(risk_id_filter)
            )

        if status_filter:
            stmt = stmt.where(CommunicationResult.status == status_filter)

        if has_risks is True:
            stmt = stmt.where(
                func.array_length(CommunicationResult.risk_ids_pred, 1) > 0
            )
        elif has_risks is False:
            stmt = stmt.where(
                or_(
                    CommunicationResult.risk_ids_pred == cast([], ARRAY(String)),
                    CommunicationResult.risk_ids_pred.is_(None),
                )
            )

        stmt = stmt.distinct()

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar() or 0

        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        stmt = stmt.order_by(Communication.created_at.desc()).limit(page_size).offset(offset)
        rows = list((await session.execute(stmt)).scalars().all())

        return PaginationResult(
            items=rows,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ------------------------------------------------------------------ #
    # Read — single communication with all results                         #
    # ------------------------------------------------------------------ #

    @connection()
    async def get_communication_with_results(
        self,
        communication_id: UUID,
        session: AsyncSession | None = None,
    ) -> Communication | None:
        """Fetch a Communication and eagerly load its results."""
        from sqlalchemy.orm import selectinload

        assert session is not None

        stmt = (
            select(Communication)
            .options(selectinload(Communication.results))
            .where(Communication.id == communication_id)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Statistics                                                            #
    # ------------------------------------------------------------------ #

    @connection()
    async def get_task_stats(
        self,
        task_id: UUID,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Compute aggregated statistics for all communications of a task.

        Returns a plain dict with keys:
          - task_id
          - total_communications
          - processed
          - with_risks
          - without_risks
          - failed
          - unique_risk_ids
          - risk_counts
          - avg_processing_time_ms
          - models_used
        """
        assert session is not None

        total: int = (
            await session.execute(
                select(func.count(Communication.id)).where(
                    Communication.task_id == task_id
                )
            )
        ).scalar() or 0

        results_stmt = select(CommunicationResult).where(
            CommunicationResult.task_id == task_id
        )
        all_results = list((await session.execute(results_stmt)).scalars().all())

        processed = len(all_results)
        with_risks = sum(1 for r in all_results if r.risk_ids_pred)
        without_risks = sum(
            1 for r in all_results if not r.risk_ids_pred and r.status == "completed"
        )
        failed = sum(1 for r in all_results if r.status == "failed")

        risk_counts: dict[str, int] = {}
        for r in all_results:
            for rid in (r.risk_ids_pred or []):
                risk_counts[rid] = risk_counts.get(rid, 0) + 1

        unique_risk_ids = sorted(risk_counts.keys())

        times = [r.processing_time_ms for r in all_results if r.processing_time_ms is not None]
        avg_time: float | None = round(sum(times) / len(times), 1) if times else None

        models_used = sorted({r.model_used for r in all_results if r.model_used})

        return {
            "task_id": task_id,
            "total_communications": total,
            "processed": processed,
            "with_risks": with_risks,
            "without_risks": without_risks,
            "failed": failed,
            "unique_risk_ids": unique_risk_ids,
            "risk_counts": risk_counts,
            "avg_processing_time_ms": avg_time,
            "models_used": models_used,
        }

    @connection()
    async def count_results_for_task(
        self,
        task_id: UUID,
        session: AsyncSession | None = None,
    ) -> int:
        """Fast count of saved results for a task."""
        assert session is not None
        return (
            await session.execute(
                select(func.count(CommunicationResult.id)).where(
                    CommunicationResult.task_id == task_id
                )
            )
        ).scalar() or 0
