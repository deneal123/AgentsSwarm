"""Refactoring cleanup: Mark legacy code as deprecated.

This migration tracks the cleanup of legacy code and the unification
of the task management architecture.

Changes:
- Marked CommunicationService, QueueService as DEPRECATED
- Marked CommunicationRepository, QueueRepository as DEPRECATED
- Marked queue.py router as DEPRECATED
- Marked communication_models.py as DEPRECATED
- Added PlaygroundLogic, PipelineLogic, FileLogic
- Updated DI container and dependencies
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "005_refactoring_cleanup"
down_revision = "004_phase5_update_api_routers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Track refactoring cleanup changes.

    This is a placeholder migration for tracking refactoring changes.
    No schema changes required - only code updates.
    """
    # no database changes needed for this placeholder migration

    # Create a refactoring log table for tracking
    op.execute("""
        CREATE TABLE IF NOT EXISTS refactoring_log (
            id SERIAL PRIMARY KEY,
            version VARCHAR(50) NOT NULL,
            description TEXT,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'
        )
    """)

    # Log this refactoring
    op.execute("""
        INSERT INTO refactoring_log (version, description, metadata)
        VALUES (
            '005_refactoring_cleanup',
            'Full refactoring cleanup: marked legacy code as deprecated',
            '{
                "deprecated_services": ["CommunicationService", "QueueService"],
                "deprecated_repositories": ["CommunicationRepository", "QueueRepository"],
                "deprecated_routers": ["queue.py"],
                "deprecated_models": ["CommunicationTask", "Communication", "CommunicationResult", "EvaluationMetrics", "Artifact"],
                "new_logic_layer": ["PlaygroundLogic", "PipelineLogic", "FileLogic"],
                "new_routers": ["playground.py", "pipeline.py", "file_uploads.py"]
            }'::jsonb
        )
    """)


def downgrade() -> None:
    """Revert refactoring cleanup changes.

    This is a placeholder for reverting refactoring changes.
    No schema changes required.
    """
    op.execute("""
        DELETE FROM refactoring_log
        WHERE version = '005_refactoring_cleanup'
    """)

    op.execute("""
        DELETE FROM alembic_version
        WHERE version_num = '005_refactoring_cleanup'
    """)