from pydantic import BaseModel, Field


class PlanningContextStats(BaseModel):
    available_changes: int = Field(ge=0)
    used_changes: int = Field(ge=0)
    available_evidence: int = Field(ge=0)
    used_evidence: int = Field(ge=0)
    available_warnings: int = Field(ge=0)
    used_warnings: int = Field(ge=0)
    truncated: bool = False


class AIUsageMetadata(BaseModel):
    model: str
    prompt_version: str
    fingerprint: str
    cache_hit: bool = False
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    context: PlanningContextStats
