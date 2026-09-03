import hashlib
import re

from app.schemas.dependency import ChangeFact, DependencyEvidence
from app.schemas.experiment import (
    ExperimentPlan,
    ExperimentStatus,
    ExperimentStep,
    ExperimentStepType,
    ExperimentTemplate,
    compute_plan_digest,
)
from app.schemas.hypothesis import FailureHypothesis

IDENTIFIER_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ExperimentCompilerError(ValueError):
    """Raised when an experiment plan cannot be safely compiled."""

    pass


def validate_identifier(name: str | None) -> str:
    if not name or not IDENTIFIER_REGEX.match(name):
        raise ExperimentCompilerError(f"Invalid or unsafe SQL identifier: {name!r}")
    return f'"{name}"'


class ExperimentCompiler:
    """Deterministic compiler converting failure hypotheses into safe experiment plans."""

    def compile(
        self,
        hypothesis: FailureHypothesis,
        changes: list[ChangeFact],
        evidence: list[DependencyEvidence],
    ) -> ExperimentPlan:
        change_map = {c.id: c for c in changes}
        for cid in hypothesis.change_ids:
            if cid not in change_map:
                raise ExperimentCompilerError(f"Hypothesis references unknown change ID: {cid!r}")

        matching_changes = [change_map[cid] for cid in hypothesis.change_ids]
        if not matching_changes:
            raise ExperimentCompilerError(
                f"Hypothesis {hypothesis.id} has no valid associated changes"
            )

        primary_change = matching_changes[0].change
        template = hypothesis.experiment_template

        steps: list[ExperimentStep] = []
        expected_observation: str = ""

        if template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE:
            table_ident = validate_identifier(primary_change.table)
            col_ident = validate_identifier(primary_change.column)
            steps = [
                ExperimentStep(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    description="Provision isolated PostgreSQL database instance",
                ),
                ExperimentStep(
                    order=2,
                    type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                    description="Apply pre-PR baseline schema migrations",
                ),
                ExperimentStep(
                    order=3,
                    type=ExperimentStepType.LOAD_SEED_DATA,
                    description="Populate representative seed data",
                ),
                ExperimentStep(
                    order=4,
                    type=ExperimentStepType.APPLY_MIGRATION,
                    description="Apply PR migration containing column drop",
                ),
                ExperimentStep(
                    order=5,
                    type=ExperimentStepType.RUN_READ_QUERY,
                    description=f"Execute reference query against removed column {col_ident}",
                    sql=f"SELECT {col_ident} FROM {table_ident} LIMIT 1;",
                ),
                ExperimentStep(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    description="Capture database response and observe if column reference fails",
                ),
            ]
            expected_observation = (
                "Query execution is expected to fail with undefined column error "
                f"on {primary_change.table}.{primary_change.column}"
            )

        elif template is ExperimentTemplate.DROPPED_TABLE_REFERENCE:
            table_ident = validate_identifier(primary_change.table)
            steps = [
                ExperimentStep(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    description="Provision isolated PostgreSQL database instance",
                ),
                ExperimentStep(
                    order=2,
                    type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                    description="Apply pre-PR baseline schema migrations",
                ),
                ExperimentStep(
                    order=3,
                    type=ExperimentStepType.LOAD_SEED_DATA,
                    description="Populate representative seed data",
                ),
                ExperimentStep(
                    order=4,
                    type=ExperimentStepType.APPLY_MIGRATION,
                    description="Apply PR migration containing table drop",
                ),
                ExperimentStep(
                    order=5,
                    type=ExperimentStepType.RUN_READ_QUERY,
                    description=f"Execute reference query against removed table {table_ident}",
                    sql=f"SELECT 1 FROM {table_ident} LIMIT 1;",
                ),
                ExperimentStep(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    description="Capture database response and observe if relation reference fails",
                ),
            ]
            expected_observation = (
                f"Query execution is expected to fail with relation does not exist error "
                f"on table {primary_change.table}"
            )

        elif template is ExperimentTemplate.NOT_NULL_COMPATIBILITY:
            table_ident = validate_identifier(primary_change.table)
            col_ident = validate_identifier(primary_change.column)
            steps = [
                ExperimentStep(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    description="Provision isolated PostgreSQL database instance",
                ),
                ExperimentStep(
                    order=2,
                    type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                    description="Apply pre-PR baseline schema migrations",
                ),
                ExperimentStep(
                    order=3,
                    type=ExperimentStepType.LOAD_SEED_DATA,
                    description="Populate representative seed data",
                ),
                ExperimentStep(
                    order=4,
                    type=ExperimentStepType.RUN_READ_QUERY,
                    description="Check for existing NULL values prior to migration",
                    sql=f"SELECT COUNT(*) FROM {table_ident} WHERE {col_ident} IS NULL;",
                ),
                ExperimentStep(
                    order=5,
                    type=ExperimentStepType.APPLY_MIGRATION,
                    description="Apply PR migration containing SET NOT NULL constraint",
                ),
                ExperimentStep(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    description="Capture database response and migration outcome",
                ),
            ]
            expected_observation = (
                f"Migration may fail if table {primary_change.table} contains rows "
                f"where column {primary_change.column} is NULL"
            )

        elif template is ExperimentTemplate.ALTER_TYPE_COMPATIBILITY:
            table_ident = validate_identifier(primary_change.table)
            col_ident = validate_identifier(primary_change.column)
            steps = [
                ExperimentStep(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    description="Provision isolated PostgreSQL database instance",
                ),
                ExperimentStep(
                    order=2,
                    type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                    description="Apply pre-PR baseline schema migrations",
                ),
                ExperimentStep(
                    order=3,
                    type=ExperimentStepType.LOAD_SEED_DATA,
                    description="Populate representative seed data",
                ),
                ExperimentStep(
                    order=4,
                    type=ExperimentStepType.APPLY_MIGRATION,
                    description="Apply PR migration containing ALTER COLUMN TYPE",
                ),
                ExperimentStep(
                    order=5,
                    type=ExperimentStepType.RUN_READ_QUERY,
                    description="Verify post-migration column read query",
                    sql=f"SELECT {col_ident} FROM {table_ident} LIMIT 1;",
                ),
                ExperimentStep(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    description="Capture database response and verify data type conversion",
                ),
            ]
            expected_observation = (
                f"Migration may fail or truncate data if existing values in {primary_change.table}."
                f"{primary_change.column} cannot be safely coerced to new type"
            )

        elif template is ExperimentTemplate.MIGRATION_APPLY:
            steps = [
                ExperimentStep(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    description="Provision isolated PostgreSQL database instance",
                ),
                ExperimentStep(
                    order=2,
                    type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                    description="Apply pre-PR baseline schema migrations",
                ),
                ExperimentStep(
                    order=3,
                    type=ExperimentStepType.LOAD_SEED_DATA,
                    description="Populate representative seed data",
                ),
                ExperimentStep(
                    order=4,
                    type=ExperimentStepType.APPLY_MIGRATION,
                    description="Apply PR migration to verify clean execution",
                ),
                ExperimentStep(
                    order=5,
                    type=ExperimentStepType.RUN_READ_QUERY,
                    description="Execute post-migration sanity read query",
                    sql="SELECT 1;",
                ),
                ExperimentStep(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    description="Capture database response and verify exit status",
                ),
            ]
            expected_observation = (
                "Migration applies cleanly without DDL syntax or dependency errors"
            )

        raw_id = f"{hypothesis.id}:{template.value}:{':'.join(hypothesis.change_ids)}"
        digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:12]
        plan_id = f"plan_{digest}"

        plan = ExperimentPlan(
            id=plan_id,
            hypothesis_id=hypothesis.id,
            template=template,
            change_ids=list(hypothesis.change_ids),
            evidence_ids=list(hypothesis.evidence_ids),
            steps=steps,
            expected_observation=expected_observation,
            status=ExperimentStatus.NOT_EXECUTED,
        )
        plan.plan_digest = compute_plan_digest(plan)
        return plan
