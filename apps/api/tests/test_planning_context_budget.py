from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    SourceScope,
)
from app.schemas.github import AnalysisWarning, AnalysisWarningCode
from app.schemas.sql_change import SqlChange, SqlOperation
from app.services.planning_context_budget import PlanningContextBudgeter


def change(identifier: str, table: str) -> ChangeFact:
    return ChangeFact(
        id=identifier,
        sql_file_path="migration.sql",
        statement_index=0,
        change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_TABLE,
            table=table,
            sql=f"DROP TABLE {table};",
        ),
    )


def evidence(
    identifier: str,
    table: str,
    *,
    scope: SourceScope = SourceScope.APPLICATION,
    kind: DependencyMatchKind = DependencyMatchKind.QUALIFIED_REFERENCE,
    changed: bool = False,
    excerpt: str = "reference",
) -> DependencyEvidence:
    return DependencyEvidence(
        id=identifier,
        target=DependencyTarget(
            type=DependencyTargetType.TABLE, table=table, change_ids=[f"c-{table}"]
        ),
        path=f"{scope.value.lower()}/{identifier}.py",
        line=1,
        match_kind=kind,
        excerpt=excerpt,
        source_scope=scope,
        changed_in_pull_request=changed,
    )


def test_budget_priority_target_coverage_caps_and_is_deterministic() -> None:
    inputs = [
        evidence("weak-test", "orders", scope=SourceScope.TEST),
        evidence("context", "orders", kind=DependencyMatchKind.TABLE_AND_COLUMN_CONTEXT),
        evidence("strong", "orders"),
        evidence("other-target", "payments", changed=True),
    ]
    budgeter = PlanningContextBudgeter(max_evidence=3)
    first = budgeter.build([], inputs, [], head_sha="head", scan_complete=True)
    second = budgeter.build([], list(reversed(inputs)), [], head_sha="head", scan_complete=True)

    assert [item.id for item in first.evidence] == [item.id for item in second.evidence]
    assert "strong" in [item.id for item in first.evidence]
    assert "other-target" in [item.id for item in first.evidence]
    assert "weak-test" not in [item.id for item in first.evidence]
    assert len(first.evidence) == 3
    assert first.context_truncated is True
    assert first.stats.truncated is True


def test_budget_truncates_changes_excerpts_and_warnings_transparently() -> None:
    budgeter = PlanningContextBudgeter(
        max_changes=1,
        max_evidence=1,
        max_excerpt_chars=5,
        max_warnings=1,
        max_warning_chars=4,
    )
    warnings = [
        AnalysisWarning(code=AnalysisWarningCode.PATCH_UNAVAILABLE, message="warning-long"),
        AnalysisWarning(code=AnalysisWarningCode.SQL_PARSE_ERROR, message="another"),
    ]
    context = budgeter.build(
        [change("c-z", "z"), change("c-a", "a")],
        [evidence("e", "a", excerpt="123456789")],
        warnings,
        head_sha="sha",
        scan_complete=False,
    )

    assert [item.id for item in context.changes] == ["c-a"]
    assert context.evidence[0].excerpt == "12345"
    assert context.warnings == ["anot"]
    assert context.stats.available_changes == 2
    assert context.stats.used_warnings == 1
    assert context.context_truncated is True
