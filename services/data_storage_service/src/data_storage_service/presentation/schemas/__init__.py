"""
Слой схем презентации (HTTP contract).

Правило разделения:
  - schemas/ — схемы запросов (Request) и HTTP-ответов, определяемые
    или re-exported здесь. Именно эти типы прописываются в response_model
    и в аннотациях параметров роутов.
  - service/models/pydantic/ — доменные модели, с которыми работают
    сервисы и репозитории.
"""

# Auth & Profile
from service.presentation.schemas.auth import (
    GuestTokenResponse,
    LogoutResponse,
    TokenRefreshRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserUpdateRequest,
    # re-exported domain responses
    LoginResponse,
    TokenRefreshResponse,
    UserResponse,
)

# File uploads
from service.presentation.schemas.file import (
    FileMetaResponse,
    FileListResponse,
    FileUploadTaskResponse,
)

# Task
from service.presentation.schemas.task import (
    TaskCancelResponse,
    TaskStatusShort,
    # re-exported domain response
    TaskResponse,
)

# Rules Marketplace
from service.presentation.schemas.rules import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleListResponse,
    RuleVersionCreate,
    RuleVersionResponse,
    UserRulePreferenceSet,
    UserRulePreferenceResponse,
    UserRulesSnapshot,
    UserRuleSnapshotEntry,
    PipelineConfigCreate,
    PipelineConfigResponse,
    RulesImportStats,
)

# Playground
from service.presentation.schemas.playground import (
    AnalyzeCommunicationRequest,
    PlaygroundTaskCancelResponse,
    PlaygroundResultsResponse,
)

# Pipeline
from service.presentation.schemas.pipeline import (
    PipelineTaskCancelResponse,
    PipelineReportSummary,
    PipelineReportDetail,
)

# Communication Results
from service.presentation.schemas.communication_results import (
    CommunicationResponse,
    CommunicationResultPage,
    CommunicationResultResponse,
    CommunicationResultSummary,
    CommunicationSummary,
    TaskCommunicationStats,
    CommunicationResultCreate,
)

__all__ = [
    # Auth
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenRefreshRequest",
    "UserUpdateRequest",
    "GuestTokenResponse",
    "LogoutResponse",
    "LoginResponse",
    "TokenRefreshResponse",
    "UserResponse",
    # Files
    "FileUploadTaskResponse",
    "FileMetaResponse",
    "FileListResponse",
    # Tasks
    "TaskResponse",
    "TaskCancelResponse",
    "TaskStatusShort",
    # Rules
    "RuleCreate",
    "RuleUpdate",
    "RuleResponse",
    "RuleListResponse",
    "RuleVersionCreate",
    "RuleVersionResponse",
    "UserRulePreferenceSet",
    "UserRulePreferenceResponse",
    "UserRulesSnapshot",
    "UserRuleSnapshotEntry",
    "PipelineConfigCreate",
    "PipelineConfigResponse",
    "RulesImportStats",
    # Playground
    "AnalyzeCommunicationRequest",
    "PlaygroundTaskCancelResponse",
    "PlaygroundResultsResponse",
    # Pipeline
    "PipelineTaskCancelResponse",
    "PipelineReportSummary",
    "PipelineReportDetail",
    # Communication Results
    "CommunicationResponse",
    "CommunicationResultPage",
    "CommunicationResultResponse",
    "CommunicationResultSummary",
    "CommunicationSummary",
    "TaskCommunicationStats",
    "CommunicationResultCreate",
]
