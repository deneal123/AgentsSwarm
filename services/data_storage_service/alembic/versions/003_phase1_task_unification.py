"""Phase 1: Task unification and concurrency management

Revision ID: 003_phase1_task_unification
Revises: 002
Create Date: 2026-02-20 10:00:00.000000

Key Changes:
- Add new fields to Task table for unified task management
- Create TaskConcurrency table for thread tracking
- Support new TaskType values (PLAYGROUND_*, PIPELINE, FILE_*)
- Add ownership fields (user_id, guest_session_id) to Task
- Add config, artifact_paths, file_id, parent_task_id fields
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '003_phase1_task_unification'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply Phase 1 schema changes"""
    
    # ========================================================================
    # SECTION 1: UPDATE TASKS TABLE
    # ========================================================================
    
    # Add ownership fields
    op.add_column(
        'tasks',
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        schema='profile'
    )
    op.add_column(
        'tasks',
        sa.Column('guest_session_id', postgresql.UUID(), nullable=True),
        schema='profile'
    )
    
    # Add new task fields
    op.add_column(
        'tasks',
        sa.Column('config', postgresql.JSONB(), nullable=True),
        schema='profile'
    )
    op.add_column(
        'tasks',
        sa.Column('artifact_paths', postgresql.ARRAY(sa.String()), nullable=True),
        schema='profile'
    )
    op.add_column(
        'tasks',
        sa.Column('file_id', postgresql.UUID(), nullable=True),
        schema='profile'
    )
    op.add_column(
        'tasks',
        sa.Column('parent_task_id', postgresql.UUID(), nullable=True),
        schema='profile'
    )
    
    # Create indexes for new fields
    op.create_index(
        'idx_tasks_user_id', 'tasks', ['user_id'],
        schema='profile'
    )
    op.create_index(
        'idx_tasks_guest_session_id', 'tasks', ['guest_session_id'],
        schema='profile'
    )
    op.create_index(
        'idx_tasks_file_id', 'tasks', ['file_id'],
        schema='profile'
    )
    op.create_index(
        'idx_tasks_parent_task_id', 'tasks', ['parent_task_id'],
        schema='profile'
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_tasks_user_id',
        'tasks', 'user',
        ['user_id'], ['id'],
        ondelete='SET NULL',
        source_schema='profile',
        referent_schema='profile'
    )
    op.create_foreign_key(
        'fk_tasks_guest_session_id',
        'tasks', 'guest_session',
        ['guest_session_id'], ['id'],
        ondelete='SET NULL',
        source_schema='profile',
        referent_schema='profile'
    )
    op.create_foreign_key(
        'fk_tasks_file_id',
        'tasks', 'files',
        ['file_id'], ['id'],
        ondelete='SET NULL',
        source_schema='profile',
        referent_schema='profile'
    )
    op.create_foreign_key(
        'fk_tasks_parent_task_id',
        'tasks', 'tasks',
        ['parent_task_id'], ['id'],
        ondelete='SET NULL',
        source_schema='profile',
        referent_schema='profile'
    )
    
    # ========================================================================
    # SECTION 2: CREATE TASK_CONCURRENCY TABLE
    # ========================================================================
    
    op.create_table(
        'task_concurrency',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(), nullable=False),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('threads_used', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', name='uq_task_concurrency_task_id'),
        sa.ForeignKeyConstraint(['task_id'], ['profile.tasks.id'], ondelete='CASCADE'),
        schema='profile',
        comment='Tracks currently running task threads for concurrency management'
    )
    
    op.create_index(
        'idx_task_concurrency_task_id', 'task_concurrency', ['task_id'],
        unique=True, schema='profile'
    )
    op.create_index(
        'idx_task_concurrency_task_type', 'task_concurrency', ['task_type'],
        schema='profile'
    )
    op.create_index(
        'idx_task_concurrency_completed_at', 'task_concurrency', ['completed_at'],
        schema='profile'
    )


def downgrade() -> None:
    """Revert Phase 1 changes"""
    
    # ========================================================================
    # SECTION 1: DROP TASK_CONCURRENCY TABLE
    # ========================================================================
    
    op.drop_index('idx_task_concurrency_completed_at', table_name='task_concurrency', schema='profile')
    op.drop_index('idx_task_concurrency_task_type', table_name='task_concurrency', schema='profile')
    op.drop_index('idx_task_concurrency_task_id', table_name='task_concurrency', schema='profile')
    op.drop_table('task_concurrency', schema='profile')
    
    # ========================================================================
    # SECTION 2: DROP TASKS TABLE CHANGES
    # ========================================================================
    
    # Drop foreign keys
    op.drop_constraint('fk_tasks_parent_task_id', 'tasks', schema='profile', type_='foreignkey')
    op.drop_constraint('fk_tasks_file_id', 'tasks', schema='profile', type_='foreignkey')
    op.drop_constraint('fk_tasks_guest_session_id', 'tasks', schema='profile', type_='foreignkey')
    op.drop_constraint('fk_tasks_user_id', 'tasks', schema='profile', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('idx_tasks_parent_task_id', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_file_id', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_guest_session_id', table_name='tasks', schema='profile')
    op.drop_index('idx_tasks_user_id', table_name='tasks', schema='profile')
    
    # Drop columns
    op.drop_column('tasks', 'parent_task_id', schema='profile')
    op.drop_column('tasks', 'file_id', schema='profile')
    op.drop_column('tasks', 'artifact_paths', schema='profile')
    op.drop_column('tasks', 'config', schema='profile')
    op.drop_column('tasks', 'guest_session_id', schema='profile')
    op.drop_column('tasks', 'user_id', schema='profile')
