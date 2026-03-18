"""Initial migration for Pushi - Risk Analysis Platform v2

Revision ID: 001_pushi_initial_v2
Revises:
Create Date: 2026-02-17 14:00:00.000000

Updated schema based on Pushi repository structure (multilabel risk classification).

Key Updates:
- Enhanced rules table with rule_id, risk_id, rule_type, product_types, channel_types
- Rule versions with additional_instructions for LLM prompts
- Pipeline configuration versioning (config.yaml snapshots)
- Communication results with triggers and reasoning
- Task-to-communication_task relation clarification
- Metrics artifacts storage

Rules Structure (from rules.toml):
  rule_id: "3.4-ВНС" (external identifier)
  risk_id: "3.4" (FK to risks)  
  rule_type: "simple" | "llm"
  product_type: ["кредит", "вклад", "ипотека"]
  channel_type: ["sms", "push", "all"]
  prompts.additional_instructions: LLM prompt

Config Structure (from config.yaml):
  paths: data directories, rules file
  mode: batch_size, concurrency settings
  llm: models, timeout, retry, temperature
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '001_pushi_initial_v2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to Pushi schema v2"""

    # ========================================================================
    # SECTION 1: SCHEMAS
    # ========================================================================
    
    op.execute('CREATE SCHEMA IF NOT EXISTS profile')
    op.execute('CREATE SCHEMA IF NOT EXISTS session')

    # ========================================================================
    # SECTION 2: USERS & AUTHENTICATION
    # ========================================================================

    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=500), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('timezone', sa.String(length=50), nullable=True, server_default='UTC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='profile',
        comment='Legal professionals'
    )
    op.create_index('idx_users_email', 'user', ['email'], unique=True, schema='profile')
    op.create_index('idx_users_is_active', 'user', ['is_active'], schema='profile')

    op.create_table(
        'user_session',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('fingerprint', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['profile.user.id'], ondelete='CASCADE'),
        schema='session',
        comment='JWT sessions'
    )
    op.create_index('idx_user_sessions_user_id', 'user_session', ['user_id'], schema='session')
    op.create_index('idx_user_sessions_token', 'user_session', ['token'], unique=True, schema='session')
    op.create_index('idx_user_sessions_status', 'user_session', ['status'], schema='session')
    op.create_index('idx_user_sessions_expires_at', 'user_session', ['expires_at'], schema='session')

    op.create_table(
        'guest_session',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_token', sa.String(), nullable=False),
        sa.Column('fingerprint', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('converted_to_user_id', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['converted_to_user_id'], ['profile.user.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Guest sessions'
    )
    op.create_index('idx_guest_sessions_token', 'guest_session', ['session_token'], unique=True, schema='profile')
    op.create_index('idx_guest_sessions_expires_at', 'guest_session', ['expires_at'], schema='profile')

    # ========================================================================
    # SECTION 3: FILE SYSTEM
    # ========================================================================

    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('storage_type', sa.String(length=20), nullable=False, server_default='local'),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('uploaded_by_user_id', postgresql.UUID(), nullable=True),
        sa.Column('uploaded_by_guest_id', postgresql.UUID(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['profile.user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_guest_id'], ['profile.guest_session.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Files: documents, rule prompts, etalons'
    )
    op.create_index('idx_files_uploaded_by_user', 'files', ['uploaded_by_user_id'], schema='profile')
    op.create_index('idx_files_file_type', 'files', ['file_type'], schema='profile')
    op.create_index('idx_files_created_at', 'files', ['created_at'], schema='profile')

    # ========================================================================
    # SECTION 4: RISK DEFINITIONS
    # ========================================================================

    op.create_table(
        'risks',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        schema='profile',
        comment='Risk catalog (e.g. "3.4" - Гарантия повышенной ставки)'
    )
    op.create_index('idx_risks_code', 'risks', ['code'], unique=True, schema='profile')
    op.create_index('idx_risks_is_active', 'risks', ['is_active'], schema='profile')
    op.create_index('idx_risks_category', 'risks', ['category'], schema='profile')

    # ========================================================================
    # SECTION 5: RULES & VERSIONING (from rules.toml structure)
    # ========================================================================

    op.create_table(
        'rules',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('risk_id', postgresql.UUID(), nullable=False),
        sa.Column('risk_category', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('consequences', sa.Text(), nullable=True),
        sa.Column('levels', sa.Text(), nullable=True),
        sa.Column('measures', sa.Text(), nullable=True),
        sa.Column('additional_information', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('risk_present_if', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('product_types', postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('channel_types', postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by_user_id', postgresql.UUID(), nullable=True),
        sa.Column('current_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id'),
        sa.ForeignKeyConstraint(['risk_id'], ['profile.risks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['profile.user.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Rules from rules.toml (e.g. "3.4-ВНС"): simple regex or LLM-based'
    )
    op.create_index('idx_rules_rule_id', 'rules', ['rule_id'], unique=True, schema='profile')
    op.create_index('idx_rules_risk_id', 'rules', ['risk_id'], schema='profile')
    op.create_index('idx_rules_rule_type', 'rules', ['rule_type'], schema='profile')
    op.create_index('idx_rules_is_active', 'rules', ['is_active'], schema='profile')
    op.create_index('idx_rules_created_by', 'rules', ['created_by_user_id'], schema='profile')

    op.create_table(
        'rule_versions',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_id', postgresql.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('additional_instructions', sa.Text(), nullable=True),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rule_id'], ['profile.rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['profile.user.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('rule_id', 'version_number', name='uq_rule_version'),
        schema='profile',
        comment='Rule prompt versioning (prompts.additional_instructions from rules.toml)'
    )
    op.create_index('idx_rule_versions_rule_id', 'rule_versions', ['rule_id'], schema='profile')
    op.create_index('idx_rule_versions_version', 'rule_versions', ['version_number'], schema='profile')
    op.create_index('idx_rule_versions_created_at', 'rule_versions', ['created_at'], schema='profile')

    # ========================================================================
    # SECTION 6: PIPELINE CONFIGURATION VERSIONING (config.yaml snapshots)
    # ========================================================================

    op.create_table(
        'pipeline_configs',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('config_data', postgresql.JSONB(), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_number'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['profile.user.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Pipeline configuration snapshots (config.yaml): batch_size, llm settings, etc'
    )
    op.create_index('idx_pipeline_configs_version', 'pipeline_configs', ['version_number'], unique=True, schema='profile')
    op.create_index('idx_pipeline_configs_is_active', 'pipeline_configs', ['is_active'], schema='profile')
    op.create_index('idx_pipeline_configs_created_at', 'pipeline_configs', ['created_at'], schema='profile')

    # ========================================================================
    # SECTION 7: COMMUNICATION PROCESSING
    # ========================================================================

    op.create_table(
        'communication_task',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('batch_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        sa.Column('guest_session_id', postgresql.UUID(), nullable=True),
        sa.Column('pipeline_config_id', postgresql.UUID(), nullable=True),
        sa.Column('product_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('total_communications', sa.Integer(), nullable=True),
        sa.Column('processed_communications', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id'),
        sa.ForeignKeyConstraint(['user_id'], ['profile.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_session_id'], ['profile.guest_session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_config_id'], ['profile.pipeline_configs.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Business entity: batch of communications for risk analysis (different from technical tasks table)'
    )
    op.create_index('idx_communication_task_batch_id', 'communication_task', ['batch_id'], unique=True, schema='profile')
    op.create_index('idx_communication_task_user_id', 'communication_task', ['user_id'], schema='profile')
    op.create_index('idx_communication_task_status', 'communication_task', ['status'], schema='profile')
    op.create_index('idx_communication_task_expires_at', 'communication_task', ['expires_at'], schema='profile')
    op.create_index('idx_communication_task_product_type', 'communication_task', ['product_type'], schema='profile')

    op.create_table(
        'communication',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('communication_id', sa.String(length=255), nullable=False),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('ai', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('product_type', sa.String(length=100), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('communication_id'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='CASCADE'),
        schema='profile',
        comment='Individual push/SMS messages for multilabel classification'
    )
    op.create_index('idx_communication_task_id', 'communication', ['task_id'], schema='profile')
    op.create_index('idx_communication_communication_id', 'communication', ['communication_id'], unique=True, schema='profile')
    op.create_index('idx_communication_product_type', 'communication', ['product_type'], schema='profile')
    op.create_index('idx_communication_type', 'communication', ['type'], schema='profile')

    op.create_table(
        'communication_result',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('communication_id', postgresql.UUID(), nullable=False),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('rule_id', postgresql.UUID(), nullable=True),
        sa.Column('risk_ids_pred', postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('risk_info', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('triggers', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['communication_id'], ['profile.communication.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['profile.rules.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Multilabel classification results with triggers and LLM reasoning'
    )
    op.create_index('idx_communication_result_communication_id', 'communication_result', ['communication_id'], schema='profile')
    op.create_index('idx_communication_result_task_id', 'communication_result', ['task_id'], schema='profile')
    op.create_index('idx_communication_result_rule_id', 'communication_result', ['rule_id'], schema='profile')
    op.create_index('idx_communication_result_status', 'communication_result', ['status'], schema='profile')

    # ========================================================================
    # SECTION 8: METRICS & ARTIFACTS
    # ========================================================================

    op.create_table(
        'evaluation_metrics',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('classification_report', postgresql.JSONB(), nullable=True),
        sa.Column('batch_time_stats', postgresql.JSONB(), nullable=True),
        sa.Column('token_statistics', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='CASCADE'),
        schema='profile',
        comment='Evaluation metrics: Micro/Macro F1, Hamming Loss, per-class metrics'
    )
    op.create_index('idx_evaluation_metrics_task_id', 'evaluation_metrics', ['task_id'], unique=True, schema='profile')
    op.create_index('idx_evaluation_metrics_created_at', 'evaluation_metrics', ['created_at'], schema='profile')

    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('artifact_type', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('file_id', postgresql.UUID(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['profile.files.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Saved artifacts: predictions.xlsx, mismatches.xlsx, plots.pdf, responses.json'
    )
    op.create_index('idx_artifacts_task_id', 'artifacts', ['task_id'], schema='profile')
    op.create_index('idx_artifacts_type', 'artifacts', ['artifact_type'], schema='profile')
    op.create_index('idx_artifacts_created_at', 'artifacts', ['created_at'], schema='profile')

    # ========================================================================
    # SECTION 9: PIPELINE QUEUE MANAGEMENT
    # ========================================================================

    op.create_table(
        'pipeline_queue',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        sa.Column('guest_session_id', postgresql.UUID(), nullable=True),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['profile.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_session_id'], ['profile.guest_session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('task_id', name='uq_pipeline_queue_task'),
        schema='profile',
        comment='Sequential processing queue (prevents parallel pipeline runs per user)'
    )
    op.create_index('idx_pipeline_queue_user_id', 'pipeline_queue', ['user_id'], schema='profile')
    op.create_index('idx_pipeline_queue_status', 'pipeline_queue', ['status'], schema='profile')
    op.create_index('idx_pipeline_queue_position', 'pipeline_queue', ['position'], schema='profile')

    # ========================================================================
    # SECTION 10: USER ACTIVITY TRACKING
    # ========================================================================

    op.create_table(
        'user_launch',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        sa.Column('guest_session_id', postgresql.UUID(), nullable=True),
        sa.Column('task_id', postgresql.UUID(), nullable=True),
        sa.Column('launch_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='initiated'),
        sa.Column('payload', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['profile.user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guest_session_id'], ['profile.guest_session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.communication_task.id'], ondelete='SET NULL'),
        schema='profile',
        comment='User activity tracking'
    )
    op.create_index('idx_user_launch_user_id', 'user_launch', ['user_id'], schema='profile')
    op.create_index('idx_user_launch_task_id', 'user_launch', ['task_id'], schema='profile')
    op.create_index('idx_user_launch_status', 'user_launch', ['status'], schema='profile')

    # ========================================================================
    # SECTION 11: ASYNC TASK MANAGEMENT (CELERY)
    # Technical tasks (Celery) - different from business communication_task
    # ========================================================================

    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('communication_task_id', postgresql.UUID(), nullable=True),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['communication_task_id'], ['profile.communication_task.id'], ondelete='SET NULL'),
        schema='profile',
        comment='Technical Celery tasks (async operations) - linked to communication_task if related'
    )
    op.create_index('idx_tasks_comm_task_id', 'tasks', ['communication_task_id'], schema='profile')
    op.create_index('idx_tasks_task_type', 'tasks', ['task_type'], schema='profile')
    op.create_index('idx_tasks_status', 'tasks', ['status'], schema='profile')
    op.create_index('idx_tasks_celery_task_id', 'tasks', ['celery_task_id'], schema='profile')
    op.create_index('idx_tasks_scheduled_at', 'tasks', ['scheduled_at'], schema='profile')


def downgrade() -> None:
    """Drop all Pushi schema objects"""

    # Drop in reverse order
    op.drop_index('idx_tasks_scheduled_at', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_celery_task_id', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_status', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_task_type', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_comm_task_id', table_name='tasks', schema='profile')
    op.drop_table('tasks', schema='profile')

    op.drop_index('idx_user_launch_status', table_name='user_launch', schema='profile')
    op.drop_index('idx_user_launch_task_id', table_name='user_launch', schema='profile')
    op.drop_index('idx_user_launch_user_id', table_name='user_launch', schema='profile')
    op.drop_table('user_launch', schema='profile')

    op.drop_index('idx_pipeline_queue_position', table_name='pipeline_queue', schema='profile')
    op.drop_index('idx_pipeline_queue_status', table_name='pipeline_queue', schema='profile')
    op.drop_index('idx_pipeline_queue_user_id', table_name='pipeline_queue', schema='profile')
    op.drop_table('pipeline_queue', schema='profile')

    op.drop_index('idx_artifacts_created_at', table_name='artifacts', schema='profile')
    op.drop_index('idx_artifacts_type', table_name='artifacts', schema='profile')
    op.drop_index('idx_artifacts_task_id', table_name='artifacts', schema='profile')
    op.drop_table('artifacts', schema='profile')

    op.drop_index('idx_evaluation_metrics_created_at', table_name='evaluation_metrics', schema='profile')
    op.drop_index('idx_evaluation_metrics_task_id', table_name='evaluation_metrics', schema='profile')
    op.drop_table('evaluation_metrics', schema='profile')

    op.drop_index('idx_communication_result_status', table_name='communication_result', schema='profile')
    op.drop_index('idx_communication_result_rule_id', table_name='communication_result', schema='profile')
    op.drop_index('idx_communication_result_task_id', table_name='communication_result', schema='profile')
    op.drop_index('idx_communication_result_communication_id', table_name='communication_result', schema='profile')
    op.drop_table('communication_result', schema='profile')

    op.drop_index('idx_communication_type', table_name='communication', schema='profile')
    op.drop_index('idx_communication_product_type', table_name='communication', schema='profile')
    op.drop_index('idx_communication_communication_id', table_name='communication', schema='profile')
    op.drop_index('idx_communication_task_id', table_name='communication', schema='profile')
    op.drop_table('communication', schema='profile')

    op.drop_index('idx_communication_task_product_type', table_name='communication_task', schema='profile')
    op.drop_index('idx_communication_task_expires_at', table_name='communication_task', schema='profile')
    op.drop_index('idx_communication_task_status', table_name='communication_task', schema='profile')
    op.drop_index('idx_communication_task_user_id', table_name='communication_task', schema='profile')
    op.drop_index('idx_communication_task_batch_id', table_name='communication_task', schema='profile')
    op.drop_table('communication_task', schema='profile')

    op.drop_index('idx_pipeline_configs_created_at', table_name='pipeline_configs', schema='profile')
    op.drop_index('idx_pipeline_configs_is_active', table_name='pipeline_configs', schema='profile')
    op.drop_index('idx_pipeline_configs_version', table_name='pipeline_configs', schema='profile')
    op.drop_table('pipeline_configs', schema='profile')

    op.drop_index('idx_rule_versions_created_at', table_name='rule_versions', schema='profile')
    op.drop_index('idx_rule_versions_version', table_name='rule_versions', schema='profile')
    op.drop_index('idx_rule_versions_rule_id', table_name='rule_versions', schema='profile')
    op.drop_table('rule_versions', schema='profile')

    op.drop_index('idx_rules_created_by', table_name='rules', schema='profile')
    op.drop_index('idx_rules_is_active', table_name='rules', schema='profile')
    op.drop_index('idx_rules_rule_type', table_name='rules', schema='profile')
    op.drop_index('idx_rules_risk_id', table_name='rules', schema='profile')
    op.drop_index('idx_rules_rule_id', table_name='rules', schema='profile')
    op.drop_table('rules', schema='profile')

    op.drop_index('idx_risks_category', table_name='risks', schema='profile')
    op.drop_index('idx_risks_is_active', table_name='risks', schema='profile')
    op.drop_index('idx_risks_code', table_name='risks', schema='profile')
    op.drop_table('risks', schema='profile')

    op.drop_index('idx_files_created_at', table_name='files', schema='profile')
    op.drop_index('idx_files_file_type', table_name='files', schema='profile')
    op.drop_index('idx_files_uploaded_by_user', table_name='files', schema='profile')
    op.drop_table('files', schema='profile')

    op.drop_index('idx_guest_sessions_expires_at', table_name='guest_session', schema='profile')
    op.drop_index('idx_guest_sessions_token', table_name='guest_session', schema='profile')
    op.drop_table('guest_session', schema='profile')

    op.drop_index('idx_user_sessions_expires_at', table_name='user_session', schema='session')
    op.drop_index('idx_user_sessions_status', table_name='user_session', schema='session')
    op.drop_index('idx_user_sessions_token', table_name='user_session', schema='session')
    op.drop_index('idx_user_sessions_user_id', table_name='user_session', schema='session')
    op.drop_table('user_session', schema='session')

    op.drop_index('idx_users_is_active', table_name='user', schema='profile')
    op.drop_index('idx_users_email', table_name='user', schema='profile')
    op.drop_table('user', schema='profile')

    op.execute('DROP SCHEMA IF EXISTS session CASCADE')
    op.execute('DROP SCHEMA IF EXISTS profile CASCADE')
