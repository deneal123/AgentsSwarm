"""
DEPRECATED: Используйте service.presentation.schemas.rules.

Этот файл оставлен для обратной совместимости.
Все схемы правил (Rules Marketplace) перенесены в schemas/rules.py.
"""

from service.presentation.schemas.rules import (  # noqa: F401
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleListResponse,
    RuleVersionCreate,
    RuleVersionResponse,
    UserRulePreferenceSet,
    UserRulePreferenceResponse,
    UserRulesSnapshot,
    PipelineConfigCreate,
    PipelineConfigResponse,
    RulesImportStats,
)

# Legacy aliases (were present in old risk.py but no longer valid)
RiskCreateRequest = None  # removed — risks merged into rules
RiskUpdateRequest = None
RiskResponse = None



class RiskUpdateRequest(BaseModel):
    """Request to update a risk."""
    
    risk_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    product_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class RiskResponse(BaseModel):
    """Response with risk details."""
    
    id: UUID
    risk_name: str
    risk_code: str
    description: Optional[str]
    category: str
    product_types: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[Dict[str, Any]]


# Rule Schemas

class RuleCreateRequest(BaseModel):
    """Request to create a new rule."""
    
    rule_name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    rule_description: Optional[str] = Field(None, max_length=1000)
    product_type: str = Field(..., description="Product type this rule applies to")
    trigger_patterns: List[str] = Field(..., min_items=1, description="Regex or keyword patterns")
    llm_reasoning_required: bool = Field(False, description="Whether LLM reasoning is required")
    llm_prompt_template: Optional[str] = Field(None, description="LLM prompt template if reasoning required")
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Confidence threshold")
    is_active: bool = Field(True)
    priority: int = Field(100, ge=1, le=1000, description="Rule priority (higher = more important)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RuleUpdateRequest(BaseModel):
    """Request to update a rule."""
    
    rule_name: Optional[str] = None
    rule_description: Optional[str] = None
    trigger_patterns: Optional[List[str]] = None
    llm_reasoning_required: Optional[bool] = None
    llm_prompt_template: Optional[str] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    metadata: Optional[Dict[str, Any]] = None


class RuleResponse(BaseModel):
    """Response with rule details."""
    
    id: UUID
    risk_id: UUID
    rule_id: str
    rule_name: str
    rule_description: Optional[str]
    product_type: str
    trigger_patterns: List[str]
    llm_reasoning_required: bool
    llm_prompt_template: Optional[str]
    confidence_threshold: float
    is_active: bool
    priority: int
    current_version_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[Dict[str, Any]]


class RuleVersionResponse(BaseModel):
    """Response with rule version details."""
    
    id: UUID
    rule_id: UUID
    version_number: int
    changes_description: Optional[str]
    created_by_user_id: Optional[UUID]
    created_at: datetime
    configuration: Dict[str, Any]


# Pipeline Configuration Schemas

class PipelineConfigCreateRequest(BaseModel):
    """Request to create pipeline configuration."""
    
    config_name: str = Field(..., min_length=1, max_length=255)
    config_yaml_content: str = Field(..., description="YAML configuration content")
    description: Optional[str] = Field(None, max_length=1000)
    is_active: bool = Field(False, description="Set as active configuration")


class PipelineConfigResponse(BaseModel):
    """Response with pipeline configuration."""
    
    id: UUID
    config_name: str
    config_yaml_content: str
    description: Optional[str]
    is_active: bool
    created_by_user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# Rules Upload Schemas

class RulesTomlUploadRequest(BaseModel):
    """Request to upload rules from TOML file."""
    
    risk_id: UUID = Field(..., description="Risk ID to associate rules with")
    toml_content: str = Field(..., description="TOML file content")
    overwrite_existing: bool = Field(False, description="Overwrite existing rules")


class RulesUploadResponse(BaseModel):
    """Response after uploading rules."""
    
    success: bool
    rules_created: int
    rules_updated: int
    rules_skipped: int
    errors: List[str]
