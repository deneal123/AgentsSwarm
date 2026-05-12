import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from service.models.db.db_models import UserLaunch
from service.models.jobs_models import JobLogic
from service.models.key_value import ProcessingStatus
from service.shared.repositories.base_repository import BaseRepository
from service.shared.repositories.decorators.session_processor import connection

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):

    @connection()
    async def create_job(self, job: JobLogic, session: AsyncSession | None = None) -> JobLogic:
        assert session is not None, "DB session is required"
        logger.debug(f"Creating job: {job}")

        new_job = UserLaunch(
            user_id=job.user_id,
            type=job.type,
            status=job.status,
            payload=job.payload,
        )
        session.add(new_job)
        await session.flush()
        return JobLogic.model_validate(new_job)

    @connection()
    async def fetch_job_by_id(
        self, job_id: UUID, user_id: UUID, session: AsyncSession | None = None
    ) -> JobLogic | None:
        assert session is not None, "DB session is required"
        logger.debug(f"Fetching job by id: {job_id} for user: {user_id}")

        stmt = select(UserLaunch).where(UserLaunch.id == job_id, UserLaunch.user_id == user_id)
        result = await session.execute(stmt)

        if db_job := result.scalar_one_or_none():
            return JobLogic.model_validate(db_job)
        return None

    @connection()
    async def fetch_jobs_by_user_id(
        self,
        user_id: UUID,
        statuses: list[ProcessingStatus],
        session: AsyncSession | None = None,
    ) -> list[JobLogic]:
        assert session is not None, "DB session is required"
        logger.debug(f"Fetching jobs for user: {user_id}")

        stmt = select(UserLaunch).where(
            UserLaunch.user_id == user_id, UserLaunch.status.in_(statuses)
        )
        result = await session.execute(stmt)
        return [JobLogic.model_validate(job) for job in result.scalars().all()]

    @connection()
    async def update_job_status(
        self, job: JobLogic, session: AsyncSession | None = None
    ) -> JobLogic | None:
        assert session is not None, "DB session is required"
        logger.debug(f"Updating job status: {job.id}")

        updating_job = UserLaunch(
            id=job.id,
            user_id=job.user_id,
            type=job.type,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            payload=job.payload,
        )
        await session.merge(updating_job)
        await session.flush()
        return JobLogic.model_validate(updating_job)

    @connection()
    async def fetch_new_jobs(
        self, limit: int = 10, session: AsyncSession | None = None
    ) -> list[JobLogic]:
        assert session is not None, "DB session is required"
        logger.debug(f"Fetching {limit} new jobs")

        stmt = (
            select(UserLaunch)
            .where(UserLaunch.status == ProcessingStatus.NEW)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        db_jobs = result.scalars().all()

        if not db_jobs:
            logger.debug("No new jobs found")
            return []

        job_ids = [job.id for job in db_jobs]
        update_stmt = (
            update(UserLaunch)
            .where(UserLaunch.id.in_(job_ids))
            .values(status=ProcessingStatus.PROCESSING)
        )
        await session.execute(update_stmt)
        await session.flush()

        updated_result = await session.execute(
            select(UserLaunch).where(UserLaunch.id.in_(job_ids))
        )
        jobs = [JobLogic.model_validate(job) for job in updated_result.scalars().all()]
        logger.debug(f"Fetched: {len(jobs)} jobs")
        return jobs

    @connection()
    async def fetch_stale_processing_jobs(
        self,
        stale_threshold_sec: int = 3600,
        limit: int = 100,
        session: AsyncSession | None = None,
    ) -> list[JobLogic]:
        assert session is not None, "DB session is required"
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_sec)
        logger.debug(f"Fetching stale PROCESSING jobs older than {cutoff}")

        stmt = (
            select(UserLaunch)
            .where(
                UserLaunch.status == ProcessingStatus.PROCESSING,
                UserLaunch.updated_at < cutoff,
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        jobs = [JobLogic.model_validate(job) for job in result.scalars().all()]
        logger.debug(f"Found {len(jobs)} stale PROCESSING jobs")
        return jobs

    @connection()
    async def delete_old_completed_jobs(
        self,
        retention_days: int = 30,
        limit: int = 500,
        session: AsyncSession | None = None,
    ) -> int:
        assert session is not None, "DB session is required"
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        logger.debug(f"Deleting completed/failed jobs older than {cutoff}")

        stmt = (
            select(UserLaunch.id)
            .where(
                UserLaunch.status.in_([ProcessingStatus.SUCCESS, ProcessingStatus.FAILURE]),
                UserLaunch.updated_at < cutoff,
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        job_ids = [row[0] for row in result.fetchall()]

        if not job_ids:
            logger.debug("No old jobs to delete")
            return 0

        await session.execute(delete(UserLaunch).where(UserLaunch.id.in_(job_ids)))
        await session.flush()

        logger.info(f"Deleted {len(job_ids)} old jobs")
        return len(job_ids)

    @connection()
    async def update_job_celery_task_id(
        self, job_id: UUID, celery_task_id: str, session: AsyncSession | None = None
    ) -> None:
        assert session is not None, "DB session is required"
        logger.debug(f"Updating job celery_task_id: {job_id}")

        stmt = (
            update(UserLaunch)
            .where(UserLaunch.id == job_id)
            .values(celery_task_id=celery_task_id)
        )
        await session.execute(stmt)
        await session.flush()
