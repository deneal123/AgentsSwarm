"""
Enums for Pushi - Risk Analysis Platform
Centralizes all enum types for legal risk detection in advertising communications
"""

import sys
from enum import Enum

# StrEnum is only available in Python 3.11+, provide fallback for 3.10
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    class StrEnum(str, Enum):
        """Fallback StrEnum for Python < 3.11"""
        def __str__(self) -> str:
            return str(self.value)

# ============================================================================
# USER AND AUTHENTICATION
# ============================================================================


class UserRole(StrEnum):
    """User role types"""

    ADMIN = "admin"
    LAWYER = "lawyer"


class UserType(StrEnum):
    """User authentication type"""

    GUEST = "guest"
    REGISTERED_USER = "registered_user"


# ============================================================================
# SESSION
# ============================================================================


class SessionStatus(StrEnum):
    """Session status types"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


# ============================================================================
# FILES
# ============================================================================


class StorageType(StrEnum):
    """File storage types"""

    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"


class FileType(StrEnum):
    """File category types for Pushi"""

    ETALON_DATASET = "etalon_dataset"
    DATASET = "dataset"
    RULE_PROMPT = "rule_prompt"
    RESULT_XLSX = "result_xlsx"
    RESULT_PDF = "result_pdf"
    RESULT_JSON = "result_json"
    CONFIG_YAML = "config_yaml"
    CONFIG = "config"


# ============================================================================
# RISKS & RULES
# ============================================================================


class RiskCategory(StrEnum):
    """Risk categories"""

    SYSTEM = "Системные риски"
    ADVERTISING = "Риски рекламной коммуникации"


class RuleType(StrEnum):
    """Rule classification type"""

    SIMPLE = "simple"
    LLM = "llm"
    COMBINED = "combined"


class ProductType(StrEnum):
    """Financial product types for targeting"""

    CREDIT = "кредит"
    CREDIT_CARD = "кредитная карта"
    DEPOSIT = "вклад"
    SAVINGS_ACCOUNT = "накопительный счет"
    MORTGAGE = "ипотека"
    ALL = "all"


class ChannelType(StrEnum):
    """Communication channel types"""

    SMS = "sms"
    PUSH = "push"
    EMAIL = "email"
    ALL = "all"


# ============================================================================
# PIPELINE SLOT (queue)
# ============================================================================


class PipelineSlotStatus(StrEnum):
    """Pipeline slot processing status"""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Legacy alias — kept for migration compatibility
PipelineQueueStatus = PipelineSlotStatus


# ============================================================================
# TASKS (UNIFIED)
# ============================================================================


class TaskStatus(StrEnum):
    """Unified task execution status"""

    NEW = "new"
    PENDING = "pending"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskType(StrEnum):
    """Unified background task types for Pushi
    
    New unified task types:
    - PLAYGROUND_*: Single/batch communication analysis
    - PIPELINE: Dataset analysis (sequential execution)
    - FILE_UPLOAD: File processing (configs, datasets)
    - MAINTENANCE: Cleanup and background tasks
    """

    # New unified types
    PLAYGROUND_SINGLE = "playground_single"      # Single communication analysis
    PLAYGROUND_BATCH = "playground_batch"        # Batch communication analysis
    PIPELINE = "pipeline"                        # Dataset pipeline (sequential)
    FILE_CONFIG_UPLOAD = "file_config_upload"    # Config file upload (.yaml, .toml)
    FILE_DATASET_UPLOAD = "file_dataset_upload"  # Dataset file upload (.xlsx)
    MAINTENANCE = "maintenance"                  # Cleanup and maintenance tasks


# ============================================================================
# USER ACTIVITY
# ============================================================================


class UserLaunchType(StrEnum):
    """User initiated actions"""

    COMMUNICATION_EVALUATION = "communication_evaluation"
    RULE_EVALUATION = "rule_evaluation"
    PIPELINE_EVALUATION = "pipeline_evaluation"
    FILE_UPLOAD = "file_upload"


class UserLaunchStatus(StrEnum):
    """User launch status"""

    INITIATED = "initiated"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# ARTIFACTS
# ============================================================================


class ArtifactType(StrEnum):
    """Generated artifact types"""

    PREDICTIONS_XLSX = "predictions_xlsx"
    MISMATCHES_XLSX = "mismatches_xlsx"
    PLOTS_PDF = "plots_pdf"
    RESPONSES_JSON = "responses_json"
    METADATA_JSON = "metadata_json"
    CONFIG_YAML = "config_yaml"
