from app.schemas.execution import (
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate

EXPECTED_SQLSTATES = {
    ExperimentTemplate.DROPPED_COLUMN_REFERENCE: "42703",
    ExperimentTemplate.DROPPED_TABLE_REFERENCE: "42P01",
    ExperimentTemplate.NOT_NULL_COMPATIBILITY: "23502",
    ExperimentTemplate.ALTER_TYPE_COMPATIBILITY: "22001",
}

FAILURE_STEPS = {
    ExperimentTemplate.DROPPED_COLUMN_REFERENCE: ExperimentStepType.RUN_READ_QUERY,
    ExperimentTemplate.DROPPED_TABLE_REFERENCE: ExperimentStepType.RUN_READ_QUERY,
    ExperimentTemplate.NOT_NULL_COMPATIBILITY: ExperimentStepType.APPLY_MIGRATION,
    ExperimentTemplate.ALTER_TYPE_COMPATIBILITY: ExperimentStepType.APPLY_MIGRATION,
}


class ExperimentVerifier:
    """Attribute verdicts only to complete, typed PostgreSQL observations."""

    def evaluate(
        self,
        template: ExperimentTemplate,
        step_results: list[ExperimentStepResult],
        *,
        expected_sqlstate: str | None = None,
    ) -> tuple[ExperimentVerdict, str]:
        step_map = {step.type: step for step in step_results}
        prep = step_map.get(ExperimentStepType.PREPARE_DATABASE)
        if prep and prep.status is ExperimentStepStatus.FAILED:
            return (
                ExperimentVerdict.EXECUTION_ERROR,
                f"Database infrastructure failure: Unable to prepare sandbox ({prep.message}).",
            )

        for step_type, label in (
            (ExperimentStepType.LOAD_BASELINE_SCHEMA, "baseline schema initialization"),
            (ExperimentStepType.LOAD_SEED_DATA, "seed data insertion"),
        ):
            step = step_map.get(step_type)
            if step and step.status is ExperimentStepStatus.FAILED:
                return (
                    ExperimentVerdict.INCONCLUSIVE,
                    f"Setup failure during {label}: {step.message}",
                )

        required = set(ExperimentStepType)
        missing = required.difference(step_map)
        if missing:
            labels = ", ".join(sorted(step.value for step in missing))
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Experiment outcome inconclusive: Missing required steps: {labels}.",
            )

        if template is ExperimentTemplate.MIGRATION_APPLY:
            if all(step_map[item].status is ExperimentStepStatus.PASSED for item in required):
                return (
                    ExperimentVerdict.PROVEN_PASS,
                    "Safe migration verified: DDL applied cleanly and every database check "
                    "succeeded in isolated sandbox.",
                )
            return (
                ExperimentVerdict.INCONCLUSIVE,
                "Safe migration verification did not complete every required step successfully.",
            )

        failure_step_type = FAILURE_STEPS.get(template)
        canonical_sqlstate = EXPECTED_SQLSTATES.get(template)
        if failure_step_type is None or canonical_sqlstate is None:
            return (
                ExperimentVerdict.INCONCLUSIVE,
                "Experiment outcome inconclusive: No deterministic verifier contract exists.",
            )
        if expected_sqlstate is not None and expected_sqlstate != canonical_sqlstate:
            return (
                ExperimentVerdict.INCONCLUSIVE,
                "Experiment outcome inconclusive: Fixture SQLSTATE contract does not match "
                "the verifier contract.",
            )

        observation = step_map[failure_step_type]
        if observation.status is ExperimentStepStatus.FAILED:
            if observation.sql_state == canonical_sqlstate:
                return (
                    ExperimentVerdict.PROVEN_FAIL,
                    "Failure reproduced in isolated PostgreSQL with expected SQLSTATE "
                    f"{canonical_sqlstate} for {template.value}.",
                )
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Observed failure had unexpected SQLSTATE {observation.sql_state}; expected "
                f"{canonical_sqlstate}. Message text is evidence only: {observation.message}",
            )

        if all(step_map[item].status is ExperimentStepStatus.PASSED for item in required):
            return (
                ExperimentVerdict.PROVEN_PASS,
                "Failure not reproduced: Every required step and the verification query "
                "completed successfully.",
            )

        return (
            ExperimentVerdict.INCONCLUSIVE,
            "Experiment outcome inconclusive: Required observations did not complete.",
        )
