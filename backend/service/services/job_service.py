import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from service.models.jobs_models import JobLogic
from service.models.key_value import ProcessingStatus
from service.models.profile_models import UserProfileLogic
from service.presentation.routers.jobs_api.schemas import StartJobRequest
from service.repositories.job_repository import JobRepository
from service.repositories.exceptions import RepositoryIntegrityError
from service.services.profile_service import ProfileService
from service.ports import JobOrchestrationPort, JobQueuePort
from service.settings import JobConfig, config
from service.chat.domain.chat_contracts import JobExecutionResult
from service.models.key_value import ServiceType

logger = logging.getLogger(__name__)

ANON_USER_UUID = UUID("00000000-0000-0000-0000-000000000000")


class JobService(JobOrchestrationPort):
    def __init__(
        self,
        config: JobConfig,
        repository: JobRepository,
        profile_source: ProfileService,
        job_queue: JobQueuePort | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.profile_source = profile_source
        self.job_queue = job_queue

    @staticmethod
    def _collect_admin_user_ids() -> list[UUID]:
        ids: list[UUID] = []
        seen: set[UUID] = set()
        for raw_admin_id in config.service.admin_user_ids_set:
            try:
                admin_uuid = UUID(str(raw_admin_id))
            except Exception:
                continue
            if admin_uuid in seen:
                continue
            ids.append(admin_uuid)
            seen.add(admin_uuid)
        return ids

    @classmethod
    def _resolve_chat_job_user_candidates(cls, user_id: UUID | None) -> list[UUID]:
        """Resolve ordered list of user ids to try for chat job persistence.

        For anonymous/invalid users we prefer configured admins first to avoid
        FK violations when ANON row is not present in DB.
        """
        admins = cls._collect_admin_user_ids()

        if user_id is None or user_id == ANON_USER_UUID:
            return admins if admins else [ANON_USER_UUID]

        candidates: list[UUID] = [user_id]
        for admin_uuid in admins:
            if admin_uuid != user_id:
                candidates.append(admin_uuid)
        return candidates

    async def create_job(self, user_id: UUID, request_body: StartJobRequest) -> JobExecutionResult:
        logger.info(
            f"Creating job for user: {user_id} with params: {request_body.type}"
        )

        user_ongoing_jobs = await self.repository.fetch_jobs_by_user_id(
            user_id, [ProcessingStatus.NEW, ProcessingStatus.PROCESSING]
        )

        # Defensive cleanup: if there are PROCESSING jobs that are stale (processing
        # started long ago), mark them as FAILURE so they don't block the user forever.
        if user_ongoing_jobs:
            now = datetime.now(timezone.utc)
            stale_threshold = max(self.config.settings.processing_timeout_sec, 60)
            stale_jobs = []
            for j in user_ongoing_jobs:
                try:
                    ts = j.updated_at or j.created_at
                    if ts is None:
                        continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    age = (now - ts).total_seconds()
                    logger.debug(
                        "Job %s: status=%s, updated_at=%s, age=%.0fs, threshold=%ds",
                        j.id,
                        j.status,
                        ts,
                        age,
                        stale_threshold,
                    )
                    if j.status == ProcessingStatus.PROCESSING and age > stale_threshold:
                        stale_jobs.append((j, age))
                except Exception as e:
                    logger.warning("Error checking job %s staleness: %s", j.id, e)
                    continue

            if stale_jobs:
                logger.warning(
                    "Found stale PROCESSING jobs for user %s: %s",
                    user_id,
                    [str(s[0].id) for s in stale_jobs],
                )
                for stale_job, age in stale_jobs:
                    try:
                        stale_job.status = ProcessingStatus.FAILURE
                        if stale_job.payload and "celery_task_id" in stale_job.payload:
                            stale_job.payload.pop("celery_task_id", None)
                        await self.repository.update_job_status(stale_job)
                        logger.info(
                            "Marked stale job %s as FAILURE (age=%.0fs) to unblock user %s",
                            stale_job.id,
                            age,
                            user_id,
                        )
                    except Exception:
                        logger.exception("Failed to mark stale job %s as FAILURE", stale_job.id)

            user_ongoing_jobs = await self.repository.fetch_jobs_by_user_id(
                user_id, [ProcessingStatus.NEW, ProcessingStatus.PROCESSING]
            )

        if user_ongoing_jobs:
            logger.error(f"User: {user_id} has an ongoing job")
            logger.debug(
                f"Ongoing jobs: {[j.model_dump_json(indent=2) for j in user_ongoing_jobs]}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has an ongoing job. Please wait for it to complete before starting a new one.",
            )

        payload: dict[str, str] = {}

        new_job = JobLogic(
            user_id=user_id,
            type=request_body.type,
            status=ProcessingStatus.NEW,
            payload=payload or None,
        )
        # TODO: If new ServiceType enum values are added (e.g., CALENDAR), ensure an alembic revision
        # updates the database enum / constraints accordingly so DB doesn't reject new values.
        created_job = await self.repository.create_job(new_job)

        logger.info(f"Job created with ID: {created_job.id} for user: {user_id}")

        wait_time = self.config.settings.wait_time_sec
        if created_job.type.name == "DEFAULT":
            wait_time = max(wait_time, self.config.settings.processing_timeout_sec)

        return JobExecutionResult(
            job_id=created_job.id,
            status=created_job.status,
            result_file_url=None,
            wait_time_sec=wait_time,
            celery_task_id=None,
        )

    async def create_calendar_job(
        self,
        user_id: UUID,
        name: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        manifest: dict | None = None,
    ) -> JobExecutionResult:
        """Create a Job of type CALENDAR and enqueue calendar generation (Celery) or run synchronously."""

        payload = {"name": name, "period_start": period_start, "period_end": period_end, "manifest": manifest}

        new_job = JobLogic(
            user_id=user_id,
            type=ServiceType.CALENDAR,
            status=ProcessingStatus.PROCESSING,
            payload=payload,
        )
        created_job = await self.repository.create_job(new_job)

        try:
            if self.job_queue:
                task_id = self.job_queue.enqueue_calendar_generation(
                    [str(created_job.id), str(user_id), name, period_start, period_end, manifest]
                )
                if task_id:
                    created_job.payload = created_job.payload or {}
                    created_job.payload["celery_task_id"] = task_id
                    updated = await self.repository.update_job_status(created_job)
                    return JobExecutionResult(
                        job_id=updated.id,
                        status=updated.status,
                        result_file_url=None,
                        wait_time_sec=self.config.settings.wait_time_sec,
                        celery_task_id=task_id,
                    )

            created_job.status = ProcessingStatus.SUCCESS
            updated = await self.repository.update_job_status(created_job)
            return JobExecutionResult(
                job_id=updated.id,
                status=updated.status,
                result_file_url=None,
                wait_time_sec=self.config.settings.wait_time_sec,
                celery_task_id=None,
            )
        except Exception as exc:
            logger.exception("Failed to create or enqueue calendar job: %s", exc)
            created_job.status = ProcessingStatus.FAILURE
            await self.repository.update_job_status(created_job)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create calendar job")

    async def create_chat_job(
        self,
        user_id: UUID | None,
        thread_id: str,
        text: str
    ) -> JobExecutionResult:
        """Create a job for agent chat message processing.

        Args:
            user_id: User ID
            thread_id: Chat thread ID
            text: User message

        Returns:
            JobResponse with job_id and status
        """
        logger.info(f"Creating chat job for user: {user_id}, thread: {thread_id}")

        payload = {
            "thread_id": thread_id,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        created_job = None
        candidates = self._resolve_chat_job_user_candidates(user_id)
        for candidate_user_id in candidates:
            try:
                new_job = JobLogic(
                    user_id=candidate_user_id,
                    type=ServiceType.CHAT,
                    status=ProcessingStatus.NEW,
                    payload=payload,
                )
                created_job = await self.repository.create_job(new_job)
                if candidate_user_id != (user_id or ANON_USER_UUID):
                    logger.warning(
                        "Chat job persisted via fallback user_id=%s for original user_id=%s",
                        candidate_user_id,
                        user_id,
                    )
                break
            except RepositoryIntegrityError:
                logger.warning(
                    "Integrity error creating chat job for user_id=%s (candidate=%s); trying next fallback",
                    user_id,
                    candidate_user_id,
                )
                continue

        if created_job is None:
            logger.error("Failed to create chat job for user_id=%s: no valid user candidate", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat job",
            )

        logger.info(f"Chat job created: {created_job.id} for user: {user_id}")

        return JobExecutionResult(
            job_id=created_job.id,
            status=created_job.status,
            result_file_url=None,
            wait_time_sec=self.config.settings.wait_time_sec,
            celery_task_id=None,
        )

    async def update_job_celery_task_id(self, job_id: UUID, celery_task_id: str) -> None:
        """Update job with Celery task ID."""
        logger.info(f"Updating job {job_id} with celery_task_id {celery_task_id}")
        await self.repository.update_job_celery_task_id(job_id, celery_task_id)

    async def fetch_job_result(self, user_id: UUID, job_id: UUID) -> JobExecutionResult:
        logger.info(f"Fetching job result for job: {job_id} and user: {user_id}")

        job = await self.repository.fetch_job_by_id(job_id, user_id)

        if not job:
            logger.error(f"Job not found for user: {user_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check Celery task status if job is still PROCESSING
        celery_task_id = job.payload.get("celery_task_id") if job.payload else None
        if job.status == ProcessingStatus.PROCESSING and celery_task_id:
            job = await self._sync_celery_status(job, celery_task_id)

        # Extract celery_task_id from job payload if present
        celery_task_id = None
        if job.payload and "celery_task_id" in job.payload:
            celery_task_id = job.payload["celery_task_id"]

        # Calculate elapsed time for PROCESSING jobs, otherwise return config value
        wait_time_sec = self.config.settings.wait_time_sec
        if job.status == ProcessingStatus.PROCESSING and job.created_at:
            created_ts = job.created_at
            if created_ts.tzinfo is None:
                created_ts = created_ts.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed_seconds = int((now - created_ts).total_seconds())
            wait_time_sec = elapsed_seconds

        return JobExecutionResult(
            job_id=job.id,
            status=job.status,
            result_file_url=None,
            wait_time_sec=wait_time_sec,
            celery_task_id=celery_task_id,
        )

    async def _sync_celery_status(self, job: JobLogic, celery_task_id: str) -> JobLogic:
        """Check Celery task status and update job if completed."""
        try:
            if not self.job_queue:
                return job
            ready, successful, result_payload, meta, state = self.job_queue.get_task_state(celery_task_id)
            if meta:
                # persist meta into job.payload for observability
                job.payload = job.payload or {}
                job.payload["meta"] = meta
                try:
                    await self.repository.update_job_status(job)
                except Exception:
                    logger.debug("Failed to persist job meta for job %s", job.id, exc_info=True)

            if ready:
                if successful:
                    job.status = ProcessingStatus.SUCCESS
                    logger.info(
                        f"Celery task {celery_task_id} completed, updating job {job.id} to SUCCESS"
                    )
                    # if the task produced a calendar_id or result, store it
                    try:
                        res = result_payload if isinstance(result_payload, dict) else None
                        if res and "calendar_id" in res:
                            job.payload = job.payload or {}
                            job.payload["calendar_id"] = res["calendar_id"]
                    except Exception:
                        logger.debug("Failed to extract result payload for job %s", job.id, exc_info=True)
                    try:
                        from service.monitoring import metrics as monmetrics
                        if monmetrics.is_enabled():
                            monmetrics.CALENDAR_JOBS_COMPLETED_TOTAL.inc()
                    except Exception:
                        logger.debug("Failed to record calendar completed metric", exc_info=True)
                else:
                    job.status = ProcessingStatus.FAILURE
                    logger.warning(
                        f"Celery task {celery_task_id} failed, updating job {job.id} to FAILURE"
                    )
                    try:
                        from service.monitoring import metrics as monmetrics
                        if monmetrics.is_enabled():
                            monmetrics.CALENDAR_JOBS_FAILED_TOTAL.inc()
                    except Exception:
                        logger.debug("Failed to record calendar failed metric", exc_info=True)

                updated_job = await self.repository.update_job_status(job)
                if updated_job:
                    return updated_job
            else:
                logger.debug(f"Celery task {celery_task_id} still running (state={state})")

        except Exception as e:
            logger.warning(f"Failed to sync Celery status for task {celery_task_id}: {e}")

        return job
