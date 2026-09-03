from app.analyzers.experiment_verifier import ExperimentVerifier
from app.schemas.execution import (
    ExperimentStepResult,
    ExperimentStepStatus,
    ExperimentVerdict,
)
from app.schemas.experiment import ExperimentStepType, ExperimentTemplate


def _step(
    order: int,
    stype: ExperimentStepType,
    status: ExperimentStepStatus,
    sql_state: str | None = None,
    message: str | None = None,
) -> ExperimentStepResult:
    return ExperimentStepResult(
        order=order,
        type=stype,
        status=status,
        duration_ms=10,
        sql_state=sql_state,
        message=message,
    )


def test_verify_dropped_column_reproduced_fail() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(4, ExperimentStepType.APPLY_MIGRATION, ExperimentStepStatus.PASSED),
        _step(
            5,
            ExperimentStepType.RUN_READ_QUERY,
            ExperimentStepStatus.FAILED,
            sql_state="42703",
            message='column "legacy_status" does not exist',
        ),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.DROPPED_COLUMN_REFERENCE, steps)
    assert verdict is ExperimentVerdict.PROVEN_FAIL
    assert "42703" in summary
    assert "Failure reproduced" in summary


def test_verify_dropped_column_not_reproduced_pass() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(4, ExperimentStepType.APPLY_MIGRATION, ExperimentStepStatus.PASSED),
        _step(5, ExperimentStepType.RUN_READ_QUERY, ExperimentStepStatus.PASSED),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.DROPPED_COLUMN_REFERENCE, steps)
    assert verdict is ExperimentVerdict.PROVEN_PASS
    assert "not reproduced" in summary.lower()


def test_verify_dropped_table_reproduced_fail() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(4, ExperimentStepType.APPLY_MIGRATION, ExperimentStepStatus.PASSED),
        _step(
            5,
            ExperimentStepType.RUN_READ_QUERY,
            ExperimentStepStatus.FAILED,
            sql_state="42P01",
            message='relation "payments" does not exist',
        ),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.DROPPED_TABLE_REFERENCE, steps)
    assert verdict is ExperimentVerdict.PROVEN_FAIL
    assert "42P01" in summary


def test_verify_not_null_compatibility_fail() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(
            4,
            ExperimentStepType.APPLY_MIGRATION,
            ExperimentStepStatus.FAILED,
            sql_state="23502",
            message='column "phone" contains null values',
        ),
        _step(5, ExperimentStepType.RUN_READ_QUERY, ExperimentStepStatus.SKIPPED),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.NOT_NULL_COMPATIBILITY, steps)
    assert verdict is ExperimentVerdict.PROVEN_FAIL
    assert "23502" in summary


def test_verify_alter_type_compatibility_fail() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(
            4,
            ExperimentStepType.APPLY_MIGRATION,
            ExperimentStepStatus.FAILED,
            sql_state="22001",
            message="value too long for type character varying(30)",
        ),
        _step(5, ExperimentStepType.RUN_READ_QUERY, ExperimentStepStatus.SKIPPED),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.ALTER_TYPE_COMPATIBILITY, steps)
    assert verdict is ExperimentVerdict.PROVEN_FAIL
    assert "22001" in summary


def test_verify_safe_additive_migration_pass() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.PASSED),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.PASSED),
        _step(4, ExperimentStepType.APPLY_MIGRATION, ExperimentStepStatus.PASSED),
        _step(5, ExperimentStepType.RUN_READ_QUERY, ExperimentStepStatus.PASSED),
        _step(6, ExperimentStepType.CAPTURE_RESULT, ExperimentStepStatus.PASSED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.MIGRATION_APPLY, steps)
    assert verdict is ExperimentVerdict.PROVEN_PASS
    assert "Safe migration verified" in summary


def test_verify_infrastructure_failure_is_execution_error() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(
            1,
            ExperimentStepType.PREPARE_DATABASE,
            ExperimentStepStatus.FAILED,
            message="Connection refused",
        ),
        _step(2, ExperimentStepType.LOAD_BASELINE_SCHEMA, ExperimentStepStatus.SKIPPED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.DROPPED_COLUMN_REFERENCE, steps)
    assert verdict is ExperimentVerdict.EXECUTION_ERROR
    assert "infrastructure failure" in summary.lower()


def test_verify_setup_failure_is_inconclusive() -> None:
    verifier = ExperimentVerifier()
    steps = [
        _step(1, ExperimentStepType.PREPARE_DATABASE, ExperimentStepStatus.PASSED),
        _step(
            2,
            ExperimentStepType.LOAD_BASELINE_SCHEMA,
            ExperimentStepStatus.FAILED,
            message="syntax error in baseline.sql",
        ),
        _step(3, ExperimentStepType.LOAD_SEED_DATA, ExperimentStepStatus.SKIPPED),
    ]

    verdict, summary = verifier.evaluate(ExperimentTemplate.DROPPED_COLUMN_REFERENCE, steps)
    assert verdict is ExperimentVerdict.INCONCLUSIVE
    assert "setup failure" in summary.lower()
