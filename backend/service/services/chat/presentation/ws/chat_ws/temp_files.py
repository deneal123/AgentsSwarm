import logging
from uuid import UUID

from service.services.agents.application.agent_file_bridge import resolve_user_uuid

logger = logging.getLogger(__name__)


class TempFilesManager:
    @staticmethod
    def register_temp_file_ids(session: dict, file_ids: list[str]) -> None:
        bucket = session.setdefault("_temp_file_ids", set())
        if not isinstance(bucket, set):
            bucket = set(bucket) if isinstance(bucket, (list, tuple)) else set()
            session["_temp_file_ids"] = bucket
        for item in file_ids:
            file_id = str(item).strip()
            if file_id:
                bucket.add(file_id)

    @staticmethod
    async def cleanup_temp_files(session: dict, file_service) -> None:
        temp_file_ids = session.get("_temp_file_ids")
        if not temp_file_ids or file_service is None:
            return
        user_uuid = resolve_user_uuid(session.get("user_id"), anonymous_fallback=True)
        if user_uuid is None:
            return
        for raw_id in list(temp_file_ids):
            try:
                await file_service.delete(user_id=user_uuid, file_id=UUID(str(raw_id)))
            except Exception:
                logger.debug("Failed to cleanup temp file %s", raw_id, exc_info=True)
