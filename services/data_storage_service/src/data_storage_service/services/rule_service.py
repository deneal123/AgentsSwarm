"""Rules Marketplace service for Pushi platform.

Responsibilities:
  - create_rule / update_rule / deactivate_rule  (admin only — enforced at router level)
  - create_rule_version                           (any authenticated user)
  - set_user_preference / get_user_preference     (per-user active version)
  - get_user_rules_snapshot                       (used by pipeline / playground)
  - PipelineConfig management                     (admin only)
  - import_rules_from_toml                        (admin bulk import)

TOML format supported for import:
  Named-table format (new, preferred):
    ["1.2-ОР"]
    rule_id = "1.2-ОР"
    rule_type = "simple"   # simple | llm | combine

    ["1.2-ОР".patterns]    # for simple / combine
    key1 = "regex1"

    ["1.2-ОР".prompts]     # for llm / combine
    additional_instructions = "..."

  Array format (legacy):
    [[rules]]
    rule_id = "1.2-ОР"
    ...
"""

from __future__ import annotations

import logging
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # backport for Python < 3.11
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from service.models.db.risk_models import Rule
from service.models.pydantic.risk import (
    PipelineConfigCreate,
    PipelineConfigResponse,
    RuleCreate,
    RuleListResponse,
    RuleResponse,
    RuleUpdate,
    RuleVersionCreate,
    RuleVersionResponse,
    UserRulePreferenceResponse,
    UserRuleSnapshotEntry,
    UserRulesSnapshot,
    UserRulePreferenceSet,
)
from service.repositories.rule_repository import RuleRepository
from service.services.base_service import BaseService
from service.utils.logging_decorators import log_operation

logger = logging.getLogger(__name__)


class RuleService(BaseService[RuleRepository]):
    """Service for managing the rules marketplace."""

    def __init__(self, repository: RuleRepository) -> None:
        super().__init__(repository)

    # ------------------------------------------------------------------ #
    # RULES — admin writes                                                  #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def create_rule(
        self, rule_data: RuleCreate, created_by_user_id: UUID
    ) -> RuleResponse:
        """Create a new rule (admin only)."""
        existing = await self.repository.get_rule_by_rule_id(rule_data.rule_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rule with rule_id '{rule_data.rule_id}' already exists",
            )

        rule = await self.repository.create_rule(
            rule_id=rule_data.rule_id,
            name=rule_data.name,
            rule_type=rule_data.rule_type,
            risk_id=rule_data.risk_id,
            risk_category=rule_data.risk_category,
            description=rule_data.description,
            consequences=rule_data.consequences,
            levels=rule_data.levels,
            measures=rule_data.measures,
            additional_information=rule_data.additional_information,
            risk_present_if=rule_data.risk_present_if,
            product_types=rule_data.product_types,
            channel_types=rule_data.channel_types,
            created_by_user_id=created_by_user_id,
            metadata=rule_data.metadata,
        )

        # Auto-create version 1
        await self.repository.create_rule_version(
            rule_uuid=rule.id,
            version_number=1,
            additional_instructions=rule_data.initial_instructions,
            patterns=rule_data.initial_patterns,
            change_description="Initial version",
            created_by_user_id=created_by_user_id,
        )

        refreshed = await self.repository.get_rule_by_id(rule.id)
        return RuleResponse.model_validate(refreshed)

    @log_operation(log_args=True)
    async def get_rule(self, rule_id: str) -> RuleResponse:
        """Get rule by human-readable rule_id."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )
        return RuleResponse.model_validate(rule)

    @log_operation(log_args=True)
    async def list_rules(
        self,
        active_only: bool = True,
        product_type: str | None = None,
        channel_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RuleListResponse]:
        """List marketplace rules."""
        rules = await self.repository.list_rules(
            active_only=active_only,
            product_type=product_type,
            channel_type=channel_type,
            limit=limit,
            offset=offset,
        )
        return [RuleListResponse.model_validate(r) for r in rules]

    @log_operation(log_args=True)
    async def update_rule(self, rule_id: str, rule_data: RuleUpdate) -> RuleResponse:
        """Update static fields of a rule (admin only)."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )
        payload = rule_data.model_dump(exclude_none=True)
        # Map metadata -> extra_metadata for DB column
        if "metadata" in payload:
            payload["extra_metadata"] = payload.pop("metadata")

        updated = await self.repository.update_rule(rule.id, payload)
        refreshed = await self.repository.get_rule_by_id(updated.id)
        return RuleResponse.model_validate(refreshed)

    @log_operation(log_args=True)
    async def deactivate_rule(self, rule_id: str) -> None:
        """Soft-delete a rule (admin only)."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )
        await self.repository.deactivate_rule(rule.id)

    # ------------------------------------------------------------------ #
    # RULE VERSIONS — any user                                              #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def create_rule_version(
        self,
        rule_id: str,
        version_data: RuleVersionCreate,
        created_by_user_id: UUID,
    ) -> RuleVersionResponse:
        """Create a new version for an existing rule (any authenticated user)."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )

        next_number = await self.repository.get_next_version_number(rule.id)
        version = await self.repository.create_rule_version(
            rule_uuid=rule.id,
            version_number=next_number,
            additional_instructions=version_data.additional_instructions,
            patterns=version_data.patterns,
            change_description=version_data.change_description,
            created_by_user_id=created_by_user_id,
            metadata=version_data.metadata,
        )
        return RuleVersionResponse.model_validate(version)

    @log_operation(log_args=True)
    async def list_rule_versions(self, rule_id: str) -> list[RuleVersionResponse]:
        """List all versions for a rule."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )
        versions = await self.repository.list_rule_versions(rule.id)
        return [RuleVersionResponse.model_validate(v) for v in versions]

    # ------------------------------------------------------------------ #
    # USER PREFERENCES — per-user active version choice                     #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def set_user_preference(
        self,
        rule_id: str,
        user_id: UUID,
        pref_data: UserRulePreferenceSet,
    ) -> UserRulePreferenceResponse:
        """Pin or unpin a version for the current user."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )

        # Validate the version exists if a pin is provided
        if pref_data.pinned_version_number is not None:
            ver = await self.repository.get_rule_version(rule.id, pref_data.pinned_version_number)
            if not ver:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Version {pref_data.pinned_version_number} not found for rule '{rule_id}'",
                )

        pref = await self.repository.set_user_preference(
            user_id=user_id,
            rule_uuid=rule.id,
            pinned_version_number=pref_data.pinned_version_number,
        )

        # Resolve effective version
        effective = await self._resolve_effective_version(rule, user_id, pref.pinned_version_number)

        return UserRulePreferenceResponse(
            rule_id=rule.rule_id,
            rule_uuid=rule.id,
            pinned_version_number=pref.pinned_version_number,
            effective_version_number=effective,
        )

    @log_operation(log_args=True)
    async def get_user_preference(
        self, rule_id: str, user_id: UUID
    ) -> UserRulePreferenceResponse:
        """Get the current user's preference for a rule."""
        rule = await self.repository.get_rule_by_rule_id(rule_id)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{rule_id}' not found",
            )

        pref = await self.repository.get_user_preference(user_id, rule.id)
        pinned = pref.pinned_version_number if pref else None
        effective = await self._resolve_effective_version(rule, user_id, pinned)

        return UserRulePreferenceResponse(
            rule_id=rule.rule_id,
            rule_uuid=rule.id,
            pinned_version_number=pinned,
            effective_version_number=effective,
        )

    async def _resolve_effective_version(
        self, rule: Rule, user_id: UUID, pinned: int | None
    ) -> int:
        """Return the version number that will actually be used for this user/rule."""
        if pinned is not None:
            return pinned
        # Latest version by this user
        user_ver = await self.repository.get_latest_version_by_user(rule.id, user_id)
        if user_ver:
            return user_ver.version_number
        # Globally latest
        global_ver = await self.repository.get_latest_version(rule.id)
        return global_ver.version_number if global_ver else rule.current_version

    # ------------------------------------------------------------------ #
    # SNAPSHOT — for pipeline / playground                                  #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def get_user_rules_snapshot(self, user_id: UUID) -> UserRulesSnapshot:
        """Resolve the full rule set with active versions for a user's run."""
        entries_raw = await self.repository.get_user_rules_snapshot(user_id)
        entries = [UserRuleSnapshotEntry(**e) for e in entries_raw]
        return UserRulesSnapshot(rules=entries, total=len(entries))

    # ------------------------------------------------------------------ #
    # PIPELINE CONFIG                                                        #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def create_pipeline_config(
        self, config_data: PipelineConfigCreate, created_by_user_id: UUID
    ) -> PipelineConfigResponse:
        """Create a new pipeline config version (admin only)."""
        configs = await self.repository.list_pipeline_configs()
        next_version = (max((c.version_number for c in configs), default=0)) + 1

        cfg = await self.repository.create_pipeline_config(
            version_number=next_version,
            config_data=config_data.config_data,
            change_description=config_data.change_description,
            created_by_user_id=created_by_user_id,
            is_active=config_data.is_active,
            metadata=config_data.metadata,
        )
        return PipelineConfigResponse.model_validate(cfg)

    @log_operation(log_args=True)
    async def get_active_pipeline_config(self) -> PipelineConfigResponse:
        """Get the currently active pipeline config."""
        cfg = await self.repository.get_active_pipeline_config()
        if not cfg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active pipeline configuration found",
            )
        return PipelineConfigResponse.model_validate(cfg)

    @log_operation(log_args=True)
    async def list_pipeline_configs(self) -> list[PipelineConfigResponse]:
        """List all pipeline config versions."""
        configs = await self.repository.list_pipeline_configs()
        return [PipelineConfigResponse.model_validate(c) for c in configs]

    @log_operation(log_args=True)
    async def activate_pipeline_config(self, config_id: UUID) -> PipelineConfigResponse:
        """Activate a pipeline config version (admin only)."""
        success = await self.repository.activate_pipeline_config(config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline config {config_id} not found",
            )
        cfg = await self.repository.get_pipeline_config_by_id(config_id)
        return PipelineConfigResponse.model_validate(cfg)

    # ------------------------------------------------------------------ #
    # BULK IMPORT from rules.toml (admin)                                   #
    # ------------------------------------------------------------------ #

    @log_operation(log_args=True)
    async def import_rules_from_toml(
        self, toml_content: str, created_by_user_id: UUID
    ) -> dict[str, int]:
        """Bulk-create rules from a rules.toml string.

        Supports two TOML layouts:

        * **Named-table format** (preferred, matches the rules.toml used by pushi)::

            ["1.2-OR"]
            rule_id  = "1.2-OR"
            rule_type = "simple"   # simple | llm | combine
            ...
            product_type = ["all"]
            channel_type = ["push"]

            ["1.2-OR".patterns]
            key = "regex"

            ["1.2-OR".prompts]
            additional_instructions = "..."

        * **Legacy array format**::

            [[rules]]
            rule_id = "1.2-OR"
            ...
        """
        try:
            data = tomllib.loads(toml_content)
        except tomllib.TOMLDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid TOML: {exc}",
            ) from exc

        # Detect format
        if "rules" in data and isinstance(data["rules"], list):
            # Legacy [[rules]] array
            entries: list[dict[str, Any]] = data["rules"]
        else:
            # Named-table: every top-level key whose value is a dict with rule_id
            entries = [
                v for v in data.values()
                if isinstance(v, dict) and v.get("rule_id")
            ]

        stats = {"rules_created": 0, "rules_skipped": 0, "versions_created": 0}

        for entry in entries:
            rid = entry.get("rule_id")
            if not rid:
                continue

            existing = await self.repository.get_rule_by_rule_id(rid)
            if existing:
                stats["rules_skipped"] += 1
                continue

            # ---- patterns (simple / combine) ----
            patterns: dict[str, str] = {}
            raw_patterns = entry.get("patterns")
            if isinstance(raw_patterns, dict):
                patterns = {k: str(v) for k, v in raw_patterns.items()}

            # ---- prompts (llm / combine) ----
            raw_prompts = entry.get("prompts", {})
            additional_instructions: str | None = None
            if isinstance(raw_prompts, dict):
                additional_instructions = raw_prompts.get("additional_instructions")
            # Also support flat additional_instructions key (legacy)
            if not additional_instructions:
                additional_instructions = entry.get("additional_instructions")

            # ---- product / channel types (TOML uses singular, DB stores plural) ----
            product_types: list[str] = (
                entry.get("product_types")
                or _to_list(entry.get("product_type", []))
            )
            channel_types: list[str] = (
                entry.get("channel_types")
                or _to_list(entry.get("channel_type", []))
            )

            rule_create = RuleCreate(
                rule_id=rid,
                risk_id=entry.get("risk_id"),
                risk_category=entry.get("risk_category"),
                name=entry.get("name", rid),
                description=entry.get("description"),
                consequences=entry.get("consequences"),
                levels=entry.get("levels"),
                measures=entry.get("measures"),
                additional_information=entry.get("additional_information"),
                rule_type=entry.get("rule_type", "simple"),
                risk_present_if=entry.get("risk_present_if", 1),
                product_types=product_types,
                channel_types=channel_types,
                initial_instructions=additional_instructions,
                initial_patterns=patterns,
                metadata=entry.get("metadata", {}),
            )
            await self.create_rule(rule_create, created_by_user_id)
            stats["rules_created"] += 1
            stats["versions_created"] += 1

        return stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_list(value: Any) -> list[str]:
    """Normalise a TOML value (string or list) to a list of strings."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value] if value else []
    return []
