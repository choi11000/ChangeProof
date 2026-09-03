from app.schemas.execution import (
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate


class ExperimentVerifier:
    """Deterministic verifier attributing PostgreSQL observations to experiment verdicts."""

    def evaluate(
        self,
        template: ExperimentTemplate,
        step_results: list[ExperimentStepResult],
        *,
        expected_sqlstate: str | None = None,
    ) -> tuple[ExperimentVerdict, str]:
        step_map = {step.type: step for step in step_results}

        # 1. Check for infrastructure failures
        prep = step_map.get(ExperimentStepType.PREPARE_DATABASE)
        if prep and prep.status is ExperimentStepStatus.FAILED:
            return (
                ExperimentVerdict.EXECUTION_ERROR,
                f"Database infrastructure failure: Unable to prepare sandbox ({prep.message}).",
            )

        # 2. Check for setup failures (Baseline schema or Seed data)
        baseline = step_map.get(ExperimentStepType.LOAD_BASELINE_SCHEMA)
        if baseline and baseline.status is ExperimentStepStatus.FAILED:
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Setup failure during baseline schema initialization: {baseline.message}",
            )

        seed = step_map.get(ExperimentStepType.LOAD_SEED_DATA)
        if seed and seed.status is ExperimentStepStatus.FAILED:
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Setup failure during seed data insertion: {seed.message}",
            )

        migration = step_map.get(ExperimentStepType.APPLY_MIGRATION)
        read_query = step_map.get(ExperimentStepType.RUN_READ_QUERY)

        # 3. Attribute verdict based on template
        if template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE:
            if migration and migration.status is ExperimentStepStatus.PASSED:
                if read_query and read_query.status is ExperimentStepStatus.FAILED:
                    msg = (read_query.message or "").lower()
                    if read_query.sql_state == "42703" or "does not exist" in msg:
                        return (
                            ExperimentVerdict.PROVEN_FAIL,
                            "Failure reproduced in isolated PostgreSQL: Column is removed by "
                            "migration and referenced query failed with SQLSTATE 42703 "
                            "(undefined_column).",
                        )
                    return (
                        ExperimentVerdict.INCONCLUSIVE,
                        f"Query failed with unexpected SQLSTATE {read_query.sql_state}: "
                        f"{read_query.message}",
                    )
                if read_query and read_query.status is ExperimentStepStatus.PASSED:
                    return (
                        ExperimentVerdict.PROVEN_PASS,
                        "Failure not reproduced: Query executed successfully without expected "
                        "column contract violation.",
                    )
            msg = migration.message if migration else "No migration step"
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Migration did not pass cleanly: {msg}",
            )

        if template is ExperimentTemplate.DROPPED_TABLE_REFERENCE:
            if migration and migration.status is ExperimentStepStatus.PASSED:
                if read_query and read_query.status is ExperimentStepStatus.FAILED:
                    msg = (read_query.message or "").lower()
                    if read_query.sql_state == "42P01" or "does not exist" in msg:
                        return (
                            ExperimentVerdict.PROVEN_FAIL,
                            "Failure reproduced in isolated PostgreSQL: Table is removed by "
                            "migration and query failed with SQLSTATE 42P01 (undefined_table).",
                        )
                    return (
                        ExperimentVerdict.INCONCLUSIVE,
                        f"Query failed with unexpected SQLSTATE {read_query.sql_state}: "
                        f"{read_query.message}",
                    )
                if read_query and read_query.status is ExperimentStepStatus.PASSED:
                    return (
                        ExperimentVerdict.PROVEN_PASS,
                        "Failure not reproduced: Table remained accessible after migration.",
                    )
            msg = migration.message if migration else "No migration step"
            return (
                ExperimentVerdict.INCONCLUSIVE,
                f"Migration did not pass cleanly: {msg}",
            )

        if template is ExperimentTemplate.NOT_NULL_COMPATIBILITY:
            if migration and migration.status is ExperimentStepStatus.FAILED:
                msg = (migration.message or "").lower()
                if migration.sql_state == "23502" or "null" in msg:
                    return (
                        ExperimentVerdict.PROVEN_FAIL,
                        "Failure reproduced in isolated PostgreSQL: Migration failed with "
                        "SQLSTATE 23502 (not_null_violation) due to existing NULL rows in "
                        "baseline seed.",
                    )
                return (
                    ExperimentVerdict.INCONCLUSIVE,
                    f"Migration failed with unexpected SQLSTATE {migration.sql_state}: "
                    f"{migration.message}",
                )
            if migration and migration.status is ExperimentStepStatus.PASSED:
                return (
                    ExperimentVerdict.PROVEN_PASS,
                    "Failure not reproduced: NOT NULL constraint applied without conflicting "
                    "null values.",
                )

        if template is ExperimentTemplate.ALTER_TYPE_COMPATIBILITY:
            if migration and migration.status is ExperimentStepStatus.FAILED:
                msg = (migration.message or "").lower()
                if migration.sql_state == "22001" or "too long" in msg or "truncat" in msg:
                    return (
                        ExperimentVerdict.PROVEN_FAIL,
                        "Failure reproduced in isolated PostgreSQL: Migration failed with "
                        "SQLSTATE 22001 (string_data_right_truncation) due to existing data "
                        "exceeding new type length.",
                    )
                return (
                    ExperimentVerdict.INCONCLUSIVE,
                    f"Migration failed with unexpected SQLSTATE {migration.sql_state}: "
                    f"{migration.message}",
                )
            if migration and migration.status is ExperimentStepStatus.PASSED:
                return (
                    ExperimentVerdict.PROVEN_PASS,
                    "Failure not reproduced: Column type alteration succeeded.",
                )

        if template is ExperimentTemplate.MIGRATION_APPLY:
            if migration and migration.status is ExperimentStepStatus.PASSED:
                return (
                    ExperimentVerdict.PROVEN_PASS,
                    "Safe migration verified: DDL applied cleanly and database checks "
                    "succeeded in isolated sandbox.",
                )
            if migration and migration.status is ExperimentStepStatus.FAILED:
                return (
                    ExperimentVerdict.PROVEN_FAIL,
                    f"Migration failed to apply with SQLSTATE {migration.sql_state}: "
                    f"{migration.message}",
                )

        return (
            ExperimentVerdict.INCONCLUSIVE,
            "Experiment outcome inconclusive: Observed results did not match expected criteria.",
        )
