from enum import StrEnum

from pydantic import BaseModel, Field


class ExperimentTemplate(StrEnum):
    MIGRATION_APPLY = "MIGRATION_APPLY"
    DROPPED_COLUMN_REFERENCE = "DROPPED_COLUMN_REFERENCE"
    DROPPED_TABLE_REFERENCE = "DROPPED_TABLE_REFERENCE"
    NOT_NULL_COMPATIBILITY = "NOT_NULL_COMPATIBILITY"
    ALTER_TYPE_COMPATIBILITY = "ALTER_TYPE_COMPATIBILITY"
    API_RESPONSE_FIELD_COMPATIBILITY = "API_RESPONSE_FIELD_COMPATIBILITY"
    EXTERNAL_DEPENDENCY_LATENCY = "EXTERNAL_DEPENDENCY_LATENCY"


class ExperimentStatus(StrEnum):
    PLANNED = "PLANNED"
    NOT_EXECUTED = "NOT_EXECUTED"


class ExperimentStepType(StrEnum):
    PREPARE_DATABASE = "PREPARE_DATABASE"
    LOAD_BASELINE_SCHEMA = "LOAD_BASELINE_SCHEMA"
    LOAD_SEED_DATA = "LOAD_SEED_DATA"
    APPLY_MIGRATION = "APPLY_MIGRATION"
    RUN_READ_QUERY = "RUN_READ_QUERY"
    CAPTURE_RESULT = "CAPTURE_RESULT"
    PREPARE_API_ENVIRONMENT = "PREPARE_API_ENVIRONMENT"
    SEND_HTTP_REQUEST = "SEND_HTTP_REQUEST"
    PROBE_RESPONSE_FIELD = "PROBE_RESPONSE_FIELD"
    CAPTURE_API_RESULT = "CAPTURE_API_RESULT"
    INITIALIZE_LOAD_ENVIRONMENT = "INITIALIZE_LOAD_ENVIRONMENT"
    RUN_BASELINE_LOAD = "RUN_BASELINE_LOAD"
    RUN_CONCURRENT_LOAD = "RUN_CONCURRENT_LOAD"
    CAPTURE_PERFORMANCE_METRICS = "CAPTURE_PERFORMANCE_METRICS"


class ExperimentStep(BaseModel):
    order: int = Field(ge=1)
    type: ExperimentStepType
    description: str
    sql: str | None = None
    endpoint: str | None = None
    method: str | None = None
    field_name: str | None = None
    concurrency: int | None = None
    request_count: int | None = None


class ExperimentPlan(BaseModel):
    id: str
    hypothesis_id: str
    template: ExperimentTemplate
    change_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    steps: list[ExperimentStep] = Field(default_factory=list)
    expected_observation: str
    status: ExperimentStatus = ExperimentStatus.NOT_EXECUTED
    plan_digest: str | None = None


def compute_plan_digest(plan: ExperimentPlan) -> str:
    import hashlib
    import json

    canonical = json.dumps(
        {
            "template": plan.template,
            "steps": [
                {
                    "order": s.order,
                    "type": s.type,
                    "sql": s.sql,
                    "endpoint": s.endpoint,
                    "field_name": s.field_name,
                    "concurrency": s.concurrency,
                    "request_count": s.request_count,
                }
                for s in plan.steps
            ],
            "expected_observation": plan.expected_observation,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
