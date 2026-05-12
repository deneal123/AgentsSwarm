import base64
import logging
from typing import Any
from uuid import UUID

from service.models.key_value import ServiceType
from service.shared.repositories.exceptions import RepositoryIntegrityError
from service.settings import config

logger = logging.getLogger(__name__)

ANON_USER_UUID = UUID("00000000-0000-0000-0000-000000000000")


def resolve_user_uuid(user_id: str | int | UUID | None, *, anonymous_fallback: bool = True) -> UUID | None:
    if isinstance(user_id, UUID):
        return user_id
    if user_id is None:
        return ANON_USER_UUID if anonymous_fallback else None

    normalized = str(user_id).strip()
    if not normalized or normalized.lower() in {"none", "null", ""}:
        return ANON_USER_UUID if anonymous_fallback else None

    try:
        return UUID(normalized)
    except Exception:
        logger.debug("Failed to convert user_id=%s to UUID", user_id)
        return ANON_USER_UUID if anonymous_fallback else None


def _collect_candidate_user_uuids(user_id: str | int | UUID | None) -> list[UUID]:
    """Build ordered list of user UUID candidates for artifact persistence.

    Priority:
    1) explicit user_id (or anon placeholder if invalid/missing)
    2) configured admin IDs as fallback for guest/invalid users
    """

    candidates: list[UUID] = []
    seen: set[UUID] = set()

    primary = resolve_user_uuid(user_id, anonymous_fallback=True)

    admin_candidates: list[UUID] = []
    admin_seen: set[UUID] = set()
    for raw_admin_id in config.service.admin_user_ids_set:
        try:
            admin_uuid = UUID(str(raw_admin_id))
        except Exception:
            continue
        if admin_uuid in admin_seen:
            continue
        admin_candidates.append(admin_uuid)
        admin_seen.add(admin_uuid)

    # For anonymous/invalid users prefer configured admin owners to avoid noisy FK failures
    # when ANON placeholder row is absent in DB.
    if primary == ANON_USER_UUID and admin_candidates:
        for admin_uuid in admin_candidates:
            if admin_uuid not in seen:
                candidates.append(admin_uuid)
                seen.add(admin_uuid)
        return candidates

    if primary is not None and primary not in seen:
        candidates.append(primary)
        seen.add(primary)

    for admin_uuid in admin_candidates:
        if admin_uuid in seen:
            continue
        candidates.append(admin_uuid)
        seen.add(admin_uuid)

    return candidates


async def persist_generated_artifacts(
    *,
    file_service,
    user_id: str | int | UUID | None,
    metadata: dict[str, Any] | None,
    job_id: str,
) -> tuple[str | None, dict[str, Any]]:
    """Persist binary artifacts produced by agent into storage and return updated metadata.

    Supports known metadata payloads:
    - pptx_b64 (+ optional filename)
    - b64_json (image bytes)
    """
    if not isinstance(metadata, dict):
        return None, metadata or {}

    user_uuid_candidates = _collect_candidate_user_uuids(user_id)
    if not user_uuid_candidates:
        return None, metadata

    out = dict(metadata)
    generated_files: list[dict[str, Any]] = []

    pptx_b64 = out.get("pptx_b64")
    if isinstance(pptx_b64, str) and pptx_b64.strip():
        try:
            pptx_bytes = base64.b64decode(pptx_b64)
            filename = str(out.get("filename") or f"presentation_{job_id}.pptx")
            if not filename.lower().endswith(".pptx"):
                filename = f"{filename}.pptx"

            saved = None
            for candidate_user_uuid in user_uuid_candidates:
                try:
                    saved = await file_service.save(
                        user_id=candidate_user_uuid,
                        mode=ServiceType.CHAT,
                        file_name=filename,
                        file_content=pptx_bytes,
                    )
                    if candidate_user_uuid != user_uuid_candidates[0]:
                        logger.warning(
                            "Persisted PPTX artifact via fallback user_id=%s for original user_id=%s",
                            candidate_user_uuid,
                            user_id,
                        )
                    break
                except RepositoryIntegrityError:
                    logger.warning(
                        "Integrity error while saving PPTX for user_id=%s (candidate=%s); trying next fallback",
                        user_id,
                        candidate_user_uuid,
                    )
                    continue

            if saved is None:
                raise RepositoryIntegrityError("No valid user candidate for PPTX artifact persistence")

            generated_files.append(
                {
                    "kind": "presentation",
                    "file_id": str(saved.file_id),
                    "file_url": saved.file_url,
                    "file_key": saved.file_key,
                    "filename": filename,
                    "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                }
            )
        except Exception:
            logger.exception("Failed to persist generated PPTX artifact for job=%s", job_id)

    image_b64 = out.get("b64_json")
    if isinstance(image_b64, str) and image_b64.strip():
        try:
            image_bytes = base64.b64decode(image_b64)
            filename = f"image_{job_id}.png"

            saved = None
            for candidate_user_uuid in user_uuid_candidates:
                try:
                    saved = await file_service.save(
                        user_id=candidate_user_uuid,
                        mode=ServiceType.CHAT,
                        file_name=filename,
                        file_content=image_bytes,
                    )
                    if candidate_user_uuid != user_uuid_candidates[0]:
                        logger.warning(
                            "Persisted image artifact via fallback user_id=%s for original user_id=%s",
                            candidate_user_uuid,
                            user_id,
                        )
                    break
                except RepositoryIntegrityError:
                    logger.warning(
                        "Integrity error while saving image for user_id=%s (candidate=%s); trying next fallback",
                        user_id,
                        candidate_user_uuid,
                    )
                    continue

            if saved is None:
                raise RepositoryIntegrityError("No valid user candidate for image artifact persistence")

            generated_files.append(
                {
                    "kind": "image",
                    "file_id": str(saved.file_id),
                    "file_url": saved.file_url,
                    "file_key": saved.file_key,
                    "filename": filename,
                    "mime_type": "image/png",
                }
            )
        except Exception:
            logger.exception("Failed to persist generated image artifact for job=%s", job_id)

    # Remove heavy inline blobs from metadata after persistence.
    out.pop("pptx_b64", None)
    out.pop("b64_json", None)

    if generated_files:
        existing = out.get("generated_files")
        if isinstance(existing, list):
            out["generated_files"] = existing + generated_files
        else:
            out["generated_files"] = generated_files

    primary_file_url = generated_files[0]["file_url"] if generated_files else None
    return primary_file_url, out
