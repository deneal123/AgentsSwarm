"""Event types for Pushi messaging system."""

from enum import StrEnum


class RiskEventType(StrEnum):
    """Risk evaluation events."""
    
    RISK_EVALUATION_STARTED = "risk_evaluation_started"
    RISK_EVALUATION_COMPLETED = "risk_evaluation_completed"
    RISK_EVALUATION_FAILED = "risk_evaluation_failed"
    RULE_MATCHED = "rule_matched"
    RULE_UPDATED = "rule_updated"
    PIPELINE_CONFIG_UPDATED = "pipeline_config_updated"


class CommunicationEventType(StrEnum):
    """Communication processing events."""
    
    COMMUNICATION_TASK_CREATED = "communication_task_created"
    COMMUNICATION_PROCESSING_STARTED = "communication_processing_started"
    COMMUNICATION_PROCESSED = "communication_processed"
    COMMUNICATION_PROCESSING_FAILED = "communication_processing_failed"
    BATCH_COMPLETED = "batch_completed"
    CLASSIFICATION_COMPLETED = "classification_completed"
    EVALUATION_COMPLETED = "evaluation_completed"


class QueueEventType(StrEnum):
    """Pipeline queue events."""
    
    TASK_ENQUEUED = "task_enqueued"
    TASK_DEQUEUED = "task_dequeued"
    TASK_PROCESSING = "task_processing"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    QUEUE_CLEARED = "queue_cleared"


class NotificationEventType(StrEnum):
    """Notification events."""
    
    EMAIL_SENT = "email_sent"
    SMS_SENT = "sms_sent"
    PUSH_SENT = "push_sent"
    NOTIFICATION_FAILED = "notification_failed"


class SystemEventType(StrEnum):
    """System maintenance events."""
    
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_COMPLETED = "cleanup_completed"
    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    HEALTH_CHECK = "health_check"
