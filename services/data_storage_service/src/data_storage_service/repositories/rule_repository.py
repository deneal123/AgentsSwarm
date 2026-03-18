"""Repository for the Rules Marketplace.

Responsibilities:
  - Rule CRUD (admin-only writes, public reads).
  - RuleVersion CRUD (any user may create versions).
  - UserRulePreference: upsert per-user active version choice.
  - get_user_rules_snapshot: resolve the effective version per rule per user
    (used by pipeline / playground to build the rule set for a run).
  - PipelineConfig management.
"""

import logging
from typing import Any
from uuid import UUID

from service.models.db.risk_models import (
    PipelineConfig,
    Rule,
    RuleVersion,
    UserRulePreference,
)
from service.repositories.base_repository import BaseRepository
from service.repositories.decorators.decorators import (
    cache,
    log_operation,
    validate_params,
)
from service.repositories.decorators.session_processor import connection
from service.repositories.exceptions import (
    RuleNotFoundError,
    raise_already_exists,
    raise_not_found,
)
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from service.utils.logger import get_logger

logger = get_logger(__name__)


class RuleRepository(BaseRepository):
    """Repository for rule management and pipeline configuration."""

    # ------------------------------------------------------------------ #
    # RULE — admin writes                                                   #
    # ------------------------------------------------------------------ #

    @log_operation(log_level=logging.INFO)
    @validate_params(rule_id=lambda x: len(x) > 0)
    @connection()
    async def create_rule(
        self,
        rule_id: str,
        name: str,
        rule_type: str,
        risk_id: str | None = None,
        risk_category: str | None = None,
        description: str | None = None,
        consequences: str | None = None,
        levels: str | None = None,
        measures: str | None = None,
        additional_information: str | None = None,
        risk_present_if: int = 1,
        product_types: list[str] | None = None,
        channel_types: list[str] | None = None,
        is_active: bool = True,
        created_by_user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> Rule:
        """Create a new rule (admin only)."""
        assert session is not None

        existing = await self.get_one_or_none(
            session=session, model=Rule, filters={"rule_id": rule_id}
        )
        if existing:
            raise_already_exists("Rule", rule_id, "rule_id")

        new_rule = Rule(
            rule_id=rule_id,
            name=name,
            rule_type=rule_type,
            risk_id=risk_id,
            risk_category=risk_category,
            description=description,
            consequences=consequences,
            levels=levels,
            measures=measures,
            additional_information=additional_information,
            risk_present_if=risk_present_if,
            product_types=product_types or [],
            channel_types=channel_types or [],
            is_active=is_active,
            created_by_user_id=created_by_user_id,
            current_version=1,
            extra_metadata=metadata or {},
        )
        session.add(new_rule)
        await session.flush()
        logger.info(f"Rule created: {new_rule.id}, rule_id={rule_id}")
        return new_rule

    @cache(ttl=300.0, namespace="rules")
    @connection()
    async def get_rule_by_id(
        self, rule_uuid: UUID, session: AsyncSession | None = None
    ) -> Rule | None:
        """Get rule by internal UUID (cached)."""
        assert session is not None
        return await self.get_one_or_none(session=session, model=Rule, filters={"id": rule_uuid})

    @cache(ttl=300.0, namespace="rules")
    @connection()
    async def get_rule_by_rule_id(
        self, rule_id: str, session: AsyncSession | None = None
    ) -> Rule | None:
        """Get rule by human-readable rule_id (cached)."""
        assert session is not None
        return await self.get_one_or_none(
            session=session, model=Rule, filters={"rule_id": rule_id}
        )

    @cache(ttl=300.0, namespace="rules")
    @validate_params(limit=lambda x: 1 <= x <= 1000)
    @connection()
    async def list_rules(
        self,
        active_only: bool = True,
        product_type: str | None = None,
        channel_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
        session: AsyncSession | None = None,
    ) -> list[Rule]:
        """List all marketplace rules with optional filters (cached)."""
        assert session is not None

        stmt = select(Rule)
        if active_only:
            stmt = stmt.where(Rule.is_active == True)
        if product_type:
            stmt = stmt.where(Rule.product_types.contains([product_type]))
        if channel_type:
            stmt = stmt.where(Rule.channel_types.contains([channel_type]))
        stmt = stmt.order_by(Rule.rule_id).limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @log_operation(log_level=logging.INFO)
    @connection()
    async def update_rule(
        self,
        rule_uuid: UUID,
        updates: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> Rule:
        """Update rule static fields (admin only)."""
        assert session is not None

        protected = {"id", "created_at", "updated_at", "rule_id"}
        values = {k: v for k, v in updates.items() if k not in protected}
        if not values:
            rule = await self.get_rule_by_id(rule_uuid, session=session)
            if not rule:
                raise RuleNotFoundError(str(rule_uuid))
            return rule

        stmt = update(Rule).where(Rule.id == rule_uuid).values(**values).returning(Rule)
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        if not rule:
            raise RuleNotFoundError(str(rule_uuid))

        logger.info(f"Rule updated: {rule_uuid}")
        return rule

    @log_operation(log_level=logging.INFO)
    @connection()
    async def deactivate_rule(
        self, rule_uuid: UUID, session: AsyncSession | None = None
    ) -> bool:
        """Soft-delete a rule (admin only)."""
        assert session is not None
        stmt = update(Rule).where(Rule.id == rule_uuid).values(is_active=False)
        result = await session.execute(stmt)
        await session.flush()
        if result.rowcount > 0:
            logger.info(f"Rule deactivated: {rule_uuid}")
            return True
        return False

    # ------------------------------------------------------------------ #
    # RULE VERSION — any user writes                                        #
    # ------------------------------------------------------------------ #

    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_rule_version(
        self,
        rule_uuid: UUID,
        version_number: int,
        additional_instructions: str | None = None,
        patterns: dict[str, Any] | None = None,
        change_description: str | None = None,
        created_by_user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> RuleVersion:
        """Create a new version for a rule and bump current_version on the rule."""
        assert session is not None

        new_version = RuleVersion(
            rule_id=rule_uuid,
            version_number=version_number,
            additional_instructions=additional_instructions,
            patterns=patterns or {},
            change_description=change_description,
            created_by_user_id=created_by_user_id,
            extra_metadata=metadata or {},
        )
        session.add(new_version)
        await session.flush()

        # Keep current_version up to date
        await session.execute(
            update(Rule)
            .where(Rule.id == rule_uuid)
            .where(Rule.current_version < version_number)
            .values(current_version=version_number)
        )
        await session.flush()

        logger.info(f"RuleVersion created: rule={rule_uuid}, version={version_number}")
        return new_version

    @cache(ttl=180.0, namespace="rule_versions")
    @connection()
    async def get_rule_version(
        self,
        rule_uuid: UUID,
        version_number: int,
        session: AsyncSession | None = None,
    ) -> RuleVersion | None:
        """Get a specific version of a rule (cached)."""
        assert session is not None
        return await self.get_one_or_none(
            session=session,
            model=RuleVersion,
            filters={"rule_id": rule_uuid, "version_number": version_number},
        )

    @cache(ttl=180.0, namespace="rule_versions")
    @connection()
    async def get_latest_version(
        self, rule_uuid: UUID, session: AsyncSession | None = None
    ) -> RuleVersion | None:
        """Get the globally latest version of a rule (cached)."""
        assert session is not None
        stmt = (
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_uuid)
            .order_by(RuleVersion.version_number.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @connection()
    async def get_latest_version_by_user(
        self,
        rule_uuid: UUID,
        user_id: UUID,
        session: AsyncSession | None = None,
    ) -> RuleVersion | None:
        """Get the latest version of a rule created by a specific user."""
        assert session is not None
        stmt = (
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_uuid)
            .where(RuleVersion.created_by_user_id == user_id)
            .order_by(RuleVersion.version_number.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @connection()
    async def list_rule_versions(
        self, rule_uuid: UUID, session: AsyncSession | None = None
    ) -> list[RuleVersion]:
        """List all versions for a rule ordered by version_number ASC."""
        assert session is not None
        stmt = (
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_uuid)
            .order_by(RuleVersion.version_number.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @connection()
    async def get_next_version_number(
        self, rule_uuid: UUID, session: AsyncSession | None = None
    ) -> int:
        """Return the next version number for a rule (max + 1)."""
        assert session is not None
        stmt = select(func.max(RuleVersion.version_number)).where(
            RuleVersion.rule_id == rule_uuid
        )
        result = await session.execute(stmt)
        max_ver = result.scalar_one_or_none()
        return (max_ver or 0) + 1

    # ------------------------------------------------------------------ #
    # USER RULE PREFERENCE — per-user active version                        #
    # ------------------------------------------------------------------ #

    @log_operation(log_level=logging.INFO)
    @connection()
    async def set_user_preference(
        self,
        user_id: UUID,
        rule_uuid: UUID,
        pinned_version_number: int | None,
        session: AsyncSession | None = None,
    ) -> UserRulePreference:
        """Upsert the user's preferred active version for a rule."""
        assert session is not None

        stmt = (
            pg_insert(UserRulePreference)
            .values(
                user_id=user_id,
                rule_id=rule_uuid,
                pinned_version_number=pinned_version_number,
            )
            .on_conflict_do_update(
                constraint="uq_user_rule_preference",
                set_={"pinned_version_number": pinned_version_number},
            )
            .returning(UserRulePreference)
        )
        result = await session.execute(stmt)
        pref = result.scalar_one()
        await session.flush()
        logger.info(f"UserRulePreference set: user={user_id}, rule={rule_uuid}, pinned={pinned_version_number}")
        return pref

    @connection()
    async def get_user_preference(
        self,
        user_id: UUID,
        rule_uuid: UUID,
        session: AsyncSession | None = None,
    ) -> UserRulePreference | None:
        """Get user's preference for a specific rule."""
        assert session is not None
        return await self.get_one_or_none(
            session=session,
            model=UserRulePreference,
            filters={"user_id": user_id, "rule_id": rule_uuid},
        )

    @connection()
    async def get_all_user_preferences(
        self, user_id: UUID, session: AsyncSession | None = None
    ) -> list[UserRulePreference]:
        """Get all rule preferences for a user."""
        assert session is not None
        stmt = select(UserRulePreference).where(UserRulePreference.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # SNAPSHOT — resolve effective versions for a user                      #
    # ------------------------------------------------------------------ #

    @connection()
    async def get_user_rules_snapshot(
        self,
        user_id: UUID,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Return the full rule set with resolved active versions for a user.

        Resolution order for each rule:
          1. User has a pinned_version_number → use that version.
          2. User has no pin → use the latest version they created.
          3. User never created a version → use the globally latest version.
          4. Rule has no versions at all → skip (should not happen after creation).
        """
        assert session is not None

        rules = await self.list_rules(active_only=True, limit=1000, session=session)
        prefs_rows = await self.get_all_user_preferences(user_id, session=session)
        prefs: dict[UUID, int | None] = {p.rule_id: p.pinned_version_number for p in prefs_rows}

        snapshot: list[dict[str, Any]] = []
        for rule in rules:
            # Determine effective version
            pinned = prefs.get(rule.id)  # None if no preference row exists

            if pinned is not None:
                # Explicit pin
                version = await self.get_rule_version(rule.id, pinned, session=session)
            else:
                # Latest version by this user
                version = await self.get_latest_version_by_user(rule.id, user_id, session=session)
                if version is None:
                    # Fallback: globally latest
                    version = await self.get_latest_version(rule.id, session=session)

            if version is None:
                # Rule has no versions — skip
                continue

            snapshot.append(
                {
                    "rule_id": rule.rule_id,
                    "rule_uuid": rule.id,
                    "name": rule.name,
                    "rule_type": rule.rule_type,
                    "risk_present_if": rule.risk_present_if,
                    "product_types": rule.product_types,
                    "channel_types": rule.channel_types,
                    "active_version_number": version.version_number,
                    "additional_instructions": version.additional_instructions,
                    "patterns": version.patterns or {},
                }
            )

        return snapshot

    # ------------------------------------------------------------------ #
    # PIPELINE CONFIG                                                        #
    # ------------------------------------------------------------------ #

    @log_operation(log_level=logging.INFO)
    @connection()
    async def create_pipeline_config(
        self,
        version_number: int,
        config_data: dict[str, Any],
        change_description: str | None = None,
        created_by_user_id: UUID | None = None,
        is_active: bool = False,
        metadata: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> PipelineConfig:
        """Create a new pipeline config version."""
        assert session is not None

        existing = await self.get_one_or_none(
            session=session, model=PipelineConfig, filters={"version_number": version_number}
        )
        if existing:
            raise_already_exists("PipelineConfig", version_number, "version_number")

        new_cfg = PipelineConfig(
            version_number=version_number,
            config_data=config_data,
            change_description=change_description,
            created_by_user_id=created_by_user_id,
            is_active=is_active,
            extra_metadata=metadata or {},
        )
        session.add(new_cfg)
        await session.flush()

        if is_active:
            await session.execute(
                update(PipelineConfig)
                .where(PipelineConfig.id != new_cfg.id)
                .values(is_active=False)
            )
            await session.flush()

        logger.info(f"PipelineConfig created: version={version_number}, active={is_active}")
        return new_cfg

    @cache(ttl=600.0, namespace="pipeline_configs")
    @connection()
    async def get_active_pipeline_config(
        self, session: AsyncSession | None = None
    ) -> PipelineConfig | None:
        """Get currently active pipeline config (cached)."""
        assert session is not None
        return await self.get_one_or_none(
            session=session, model=PipelineConfig, filters={"is_active": True}
        )

    @cache(ttl=300.0, namespace="pipeline_configs")
    @connection()
    async def get_pipeline_config_by_id(
        self, config_id: UUID, session: AsyncSession | None = None
    ) -> PipelineConfig | None:
        """Get pipeline config by ID (cached)."""
        assert session is not None
        return await self.get_one_or_none(
            session=session, model=PipelineConfig, filters={"id": config_id}
        )

    @connection()
    async def list_pipeline_configs(
        self, session: AsyncSession | None = None
    ) -> list[PipelineConfig]:
        """List all pipeline config versions ordered by version_number DESC."""
        assert session is not None
        stmt = select(PipelineConfig).order_by(PipelineConfig.version_number.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @log_operation(log_level=logging.INFO)
    @connection()
    async def activate_pipeline_config(
        self, config_id: UUID, session: AsyncSession | None = None
    ) -> bool:
        """Activate a pipeline config version, deactivating all others."""
        assert session is not None
        await session.execute(update(PipelineConfig).values(is_active=False))
        stmt = (
            update(PipelineConfig)
            .where(PipelineConfig.id == config_id)
            .values(is_active=True)
        )
        result = await session.execute(stmt)
        await session.flush()
        if result.rowcount > 0:
            logger.info(f"PipelineConfig activated: {config_id}")
            return True
        return False

