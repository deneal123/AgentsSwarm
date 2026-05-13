import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from service.models.jobs_models import JobLogic
from service.models.key_value import ProcessingStatus, ServiceType
from service.services.chat.domain.chat_contracts import JobExecutionResult
from service.services.jobs.application.dto import StartJobRequest
from service.services.jobs.application.ports.interfaces import JobOrchestrationPort, JobQueuePort
from service.services.jobs.persistence.job_repository import JobRepository
from service.settings import JobConfig, config
from service.shared.repositories.exceptions import RepositoryIntegrityError

logger = logging.getLogger(__name__)

ANON_USER_UUID = UUID("00000000-0000-0000-0000-000000000000")


class JobService(JobOrchestrationPort):
    def __init__(
        self,
        config: JobConfig,
        repository: JobRepository,
        job_queue: JobQueuePort | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
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
        logger.info(f"Creating job for user: {user_id} with params: {request_body.type}")

        user_ongoing_jobs = await self.repository.fetch_jobs_by_user_id(
            user_id, [ProcessingStatus.NEW, ProcessingStatus.PROCESSING]
        )

        # Defensive cleanup: if there are PROCESSING jobs that are stale (processing
        # started long ago), mark them as FAILURE so they don't block the user forever.
        if user_ongoing_jobs:
            now = datetime.now(UTC)
            stale_threshold = max(self.config.settings.processing_timeout_sec, 60)
            stale_jobs = []
            for j in user_ongoing_jobs:
                try:
                    ts = j.updated_at or j.created_at
                    if ts is None:
                        continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
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
        created_job = await self.repository.create_job(new_job)

        logger.info(f"Job created with ID: {created_job.id} for user: {user_id}")

        wait_time = self._resolve_wait_time(created_job.type)

        return JobExecutionResult(
            job_id=created_job.id,
            status=created_job.status,
            result_file_url=None,
            wait_time_sec=wait_time,
            celery_task_id=None,
        )

    def _resolve_wait_time(self, job_type: ServiceType) -> int:
        return self.config.settings.wait_time_sec

    async def create_chat_job(
        self, user_id: UUID | None, thread_id: str, text: str
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
            "created_at": datetime.now(UTC).isoformat(),
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
            logger.error(
                "Failed to create chat job for user_id=%s: no valid user candidate", user_id
            )
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
                created_ts = created_ts.replace(tzinfo=UTC)
            now = datetime.now(UTC)
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
            ready, successful, result_payload, meta, state = self.job_queue.get_task_state(
                celery_task_id
            )
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
                else:
                    job.status = ProcessingStatus.FAILURE
                    logger.warning(
                        f"Celery task {celery_task_id} failed, updating job {job.id} to FAILURE"
                    )
                updated_job = await self.repository.update_job_status(job)
                if updated_job:
                    return updated_job
            else:
                logger.debug(f"Celery task {celery_task_id} still running (state={state})")

        except Exception as e:
            logger.warning(f"Failed to sync Celery status for task {celery_task_id}: {e}")

        return job
