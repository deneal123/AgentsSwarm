from pydantic import BaseModel, Field


class MemoryFactResponse(BaseModel):
    id: str
    fact_type: str
    fact_key: str
    fact_value: str
    confidence: float | None = None
    updated_at: str | None = None


class MemoryFactsResponse(BaseModel):
    facts: list[MemoryFactResponse] = Field(default_factory=list)
    context_text: str | None = None


class AddMemoryFactRequest(BaseModel):
    user_id: str | None = None
    fact_type: str = "general"
    fact_key: str = Field(..., min_length=1)
    fact_value: str = Field(..., min_length=1)


class AddMemoryFactResponse(BaseModel):
    fact: MemoryFactResponse
