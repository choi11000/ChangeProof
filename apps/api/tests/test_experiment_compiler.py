import pytest

from app.analyzers.experiment_compiler import (
    ExperimentCompiler,
    ExperimentCompilerError,
    validate_identifier,
)
from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    SourceScope,
)
from app.schemas.experiment import (
    ExperimentStatus,
    ExperimentStepType,
    ExperimentTemplate,
)
from app.schemas.hypothesis import FailureCategory, FailureHypothesis, HypothesisStatus
from app.schemas.sql_change import SqlChange, SqlOperation


def _fact(cid: str, op: SqlOperation, table: str, column: str | None = None) -> ChangeFact:
    return ChangeFact(
        id=cid,
        sql_file_path="migrations/001.sql",
        statement_index=0,
        change=SqlChange(
            statement_index=0,
            operation=op,
            table=table,
            column=column,
            sql=f"ALTER TABLE {table} ...",
        ),
    )


def _evidence(eid: str, table: str, column: str) -> DependencyEvidence:
    return DependencyEvidence(
        id=eid,
        target=DependencyTarget(
            type=DependencyTargetType.COLUMN,
            table=table,
            column=column,
            change_ids=["c1"],
        ),
        path="app/order.py",
        line=10,
        match_kind=DependencyMatchKind.QUALIFIED_REFERENCE,
        excerpt="return order.legacy_status",
        source_scope=SourceScope.APPLICATION,
    )


def test_compile_dropped_column_reference() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_01",
        category=FailureCategory.SCHEMA_CONTRACT_BREAK,
        title="Dropped column remains referenced",
        statement="Application still references orders.legacy_status",
        change_ids=["c1"],
        evidence_ids=["ev1"],
        rationale="Migration removes column used by order_service.py",
        expected_failure_mode="UndefinedColumn error",
        assumptions=["Baseline contains orders table"],
        experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
        status=HypothesisStatus.UNVERIFIED,
    )
    change = _fact("c1", SqlOperation.DROP_COLUMN, "orders", "legacy_status")
    ev = _evidence("ev1", "orders", "legacy_status")

    plan = compiler.compile(hypothesis, [change], [ev])

    assert plan.hypothesis_id == "hyp_01"
    assert plan.template is ExperimentTemplate.DROPPED_COLUMN_REFERENCE
    assert plan.status is ExperimentStatus.NOT_EXECUTED
    assert len(plan.steps) == 6

    step_types = [s.type for s in plan.steps]
    assert step_types == [
        ExperimentStepType.PREPARE_DATABASE,
        ExperimentStepType.LOAD_BASELINE_SCHEMA,
        ExperimentStepType.LOAD_SEED_DATA,
        ExperimentStepType.APPLY_MIGRATION,
        ExperimentStepType.RUN_READ_QUERY,
        ExperimentStepType.CAPTURE_RESULT,
    ]

    read_step = plan.steps[4]
    assert read_step.sql == 'SELECT "legacy_status" FROM "orders" LIMIT 1;'
    assert "undefined column" in plan.expected_observation.lower()


def test_compile_dropped_table_reference() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_02",
        category=FailureCategory.TABLE_CONTRACT_BREAK,
        title="Dropped table remains referenced",
        statement="Application still references payments",
        change_ids=["c2"],
        evidence_ids=[],
        rationale="Migration removes payments table",
        expected_failure_mode="RelationDoesNotExist error",
        assumptions=[],
        experiment_template=ExperimentTemplate.DROPPED_TABLE_REFERENCE,
    )
    change = _fact("c2", SqlOperation.DROP_TABLE, "payments", None)

    plan = compiler.compile(hypothesis, [change], [])

    assert plan.template is ExperimentTemplate.DROPPED_TABLE_REFERENCE
    assert plan.status is ExperimentStatus.NOT_EXECUTED
    read_step = next(s for s in plan.steps if s.type is ExperimentStepType.RUN_READ_QUERY)
    assert read_step.sql == 'SELECT 1 FROM "payments" LIMIT 1;'


def test_compile_not_null_compatibility() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_03",
        category=FailureCategory.NULLABILITY_COMPATIBILITY,
        title="Null values conflict with NOT NULL constraint",
        statement="users.display_name may contain NULLs",
        change_ids=["c3"],
        evidence_ids=[],
        rationale="SET NOT NULL requires existing rows to be non-null",
        expected_failure_mode="NotNullViolation",
        assumptions=[],
        experiment_template=ExperimentTemplate.NOT_NULL_COMPATIBILITY,
    )
    change = _fact("c3", SqlOperation.SET_NOT_NULL, "users", "display_name")

    plan = compiler.compile(hypothesis, [change], [])

    assert plan.template is ExperimentTemplate.NOT_NULL_COMPATIBILITY
    read_step = next(s for s in plan.steps if s.type is ExperimentStepType.RUN_READ_QUERY)
    assert read_step.sql == 'SELECT COUNT(*) FROM "users" WHERE "display_name" IS NULL;'


def test_compile_alter_type_compatibility() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_04",
        category=FailureCategory.TYPE_COMPATIBILITY,
        title="Type alteration may truncate or fail conversion",
        statement="users.email altered to varchar(30)",
        change_ids=["c4"],
        evidence_ids=[],
        rationale="Type change compatibility check",
        expected_failure_mode="DatatypeMismatch",
        assumptions=[],
        experiment_template=ExperimentTemplate.ALTER_TYPE_COMPATIBILITY,
    )
    change = _fact("c4", SqlOperation.ALTER_COLUMN_TYPE, "users", "email")

    plan = compiler.compile(hypothesis, [change], [])

    assert plan.template is ExperimentTemplate.ALTER_TYPE_COMPATIBILITY
    read_step = next(s for s in plan.steps if s.type is ExperimentStepType.RUN_READ_QUERY)
    assert read_step.sql == 'SELECT "email" FROM "users" LIMIT 1;'


def test_compiler_rejects_unknown_change_id() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_err",
        category=FailureCategory.SCHEMA_CONTRACT_BREAK,
        title="Test",
        statement="Test",
        change_ids=["unknown_change"],
        evidence_ids=[],
        rationale="Test",
        expected_failure_mode="Test",
        assumptions=[],
        experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
    )

    with pytest.raises(ExperimentCompilerError, match="unknown change ID"):
        compiler.compile(hypothesis, [], [])


def test_compiler_rejects_invalid_identifier() -> None:
    with pytest.raises(ExperimentCompilerError, match="Invalid or unsafe SQL identifier"):
        validate_identifier("orders; DROP DATABASE production;--")

    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_inject",
        category=FailureCategory.SCHEMA_CONTRACT_BREAK,
        title="Injection attempt",
        statement="Testing safety",
        change_ids=["c_bad"],
        evidence_ids=[],
        rationale="Test",
        expected_failure_mode="Test",
        assumptions=[],
        experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
    )
    bad_change = _fact("c_bad", SqlOperation.DROP_COLUMN, "orders; DROP TABLE secrets;--", "col")

    with pytest.raises(ExperimentCompilerError, match="Invalid or unsafe SQL identifier"):
        compiler.compile(hypothesis, [bad_change], [])


def test_compiler_never_emits_shell_command() -> None:
    compiler = ExperimentCompiler()
    hypothesis = FailureHypothesis(
        id="hyp_safe",
        category=FailureCategory.SCHEMA_CONTRACT_BREAK,
        title="Safe Check",
        statement="Checking safe steps",
        change_ids=["c_safe"],
        evidence_ids=[],
        rationale="Safe",
        expected_failure_mode="Safe",
        assumptions=[],
        experiment_template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
    )
    change = _fact("c_safe", SqlOperation.DROP_COLUMN, "orders", "status")

    plan = compiler.compile(hypothesis, [change], [])

    forbidden_tokens = ["docker", "rm ", "curl", "bash", "sh ", "exec ", "sudo"]
    for step in plan.steps:
        desc_lower = step.description.lower()
        sql_lower = (step.sql or "").lower()
        for token in forbidden_tokens:
            assert token not in desc_lower
            assert token not in sql_lower
