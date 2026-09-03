from app.analyzers.dependency import (
    DependencyAnalyzer,
    extract_dependency_targets,
    get_column_variants,
    get_table_variants,
    summarize_impact,
)
from app.schemas.dependency import (
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    SourceDocument,
    SourceScope,
)
from app.schemas.github import ChangedFileStatus, ContentSource, SqlAnalysisResult, SqlFileAnalysis
from app.schemas.sql_change import SqlChange, SqlOperation


def test_extract_column_dependency_targets() -> None:
    sql_files = [
        SqlFileAnalysis(
            path="migrations/001.sql",
            status=ChangedFileStatus.MODIFIED,
            content_source=ContentSource.HEAD,
            analysis=SqlAnalysisResult(
                changes=[
                    SqlChange(
                        statement_index=0,
                        operation=SqlOperation.DROP_COLUMN,
                        table="orders",
                        column="legacy_status",
                        sql="ALTER TABLE orders DROP COLUMN legacy_status;",
                    ),
                    SqlChange(
                        statement_index=1,
                        operation=SqlOperation.ALTER_COLUMN_TYPE,
                        table="users",
                        column="email",
                        data_type="VARCHAR(30)",
                        sql="ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(30);",
                    ),
                    SqlChange(
                        statement_index=2,
                        operation=SqlOperation.SET_NOT_NULL,
                        table="users",
                        column="phone",
                        sql="ALTER TABLE users ALTER COLUMN phone SET NOT NULL;",
                    ),
                ]
            ),
        )
    ]

    targets = extract_dependency_targets(sql_files)

    assert len(targets) == 3
    assert targets[0].type is DependencyTargetType.COLUMN
    assert targets[0].table == "orders"
    assert targets[0].column == "legacy_status"
    assert targets[1].table == "users"
    assert targets[1].column == "email"
    assert targets[2].table == "users"
    assert targets[2].column == "phone"


def test_extract_table_dependency_targets() -> None:
    sql_files = [
        SqlFileAnalysis(
            path="migrations/004.sql",
            status=ChangedFileStatus.MODIFIED,
            content_source=ContentSource.HEAD,
            analysis=SqlAnalysisResult(
                changes=[
                    SqlChange(
                        statement_index=0,
                        operation=SqlOperation.DROP_TABLE,
                        table="payments",
                        sql="DROP TABLE payments;",
                    ),
                ]
            ),
        )
    ]

    targets = extract_dependency_targets(sql_files)

    assert len(targets) == 1
    assert targets[0].type is DependencyTargetType.TABLE
    assert targets[0].table == "payments"
    assert targets[0].column is None


def test_extract_targets_ignores_non_destructive_or_unsupported_ops() -> None:
    sql_files = [
        SqlFileAnalysis(
            path="migrations/000.sql",
            status=ChangedFileStatus.ADDED,
            content_source=ContentSource.HEAD,
            analysis=SqlAnalysisResult(
                changes=[
                    SqlChange(
                        statement_index=0,
                        operation=SqlOperation.CREATE_TABLE,
                        table="logs",
                        sql="CREATE TABLE logs (id INT);",
                    ),
                    SqlChange(
                        statement_index=1,
                        operation=SqlOperation.ADD_COLUMN,
                        table="logs",
                        column="created_at",
                        sql="ALTER TABLE logs ADD COLUMN created_at TIMESTAMP;",
                    ),
                    SqlChange(
                        statement_index=2,
                        operation=SqlOperation.CREATE_INDEX,
                        table="logs",
                        index="idx_logs",
                        sql="CREATE INDEX idx_logs ON logs (created_at);",
                    ),
                ]
            ),
        )
    ]

    targets = extract_dependency_targets(sql_files)
    assert len(targets) == 0


def test_get_column_variants() -> None:
    variants = get_column_variants("legacy_status")
    assert "legacy_status" in variants
    assert "legacyStatus" in variants
    assert "LegacyStatus" in variants


def test_get_table_variants() -> None:
    variants = get_table_variants("orders")
    assert "orders" in variants
    assert "order" in variants
    assert "Orders" in variants
    assert "Order" in variants


def test_find_qualified_reference() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="orders",
        column="legacy_status",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
        ),
    )
    doc = SourceDocument(
        path="app/order_service.py",
        scope=SourceScope.APPLICATION,
        content=(
            "class OrderService:\n"
            "    def get_status(self, order):\n"
            "        return order.legacy_status\n"
        ),
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) == 1
    assert evidences[0].path == "app/order_service.py"
    assert evidences[0].line == 3
    assert evidences[0].match_kind is DependencyMatchKind.QUALIFIED_REFERENCE
    assert "return order.legacy_status" in evidences[0].excerpt


def test_find_table_and_column_context() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="orders",
        column="legacy_status",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
        ),
    )
    doc = SourceDocument(
        path="app/db.py",
        scope=SourceScope.APPLICATION,
        content=(
            "# fetch from orders\n"
            "query = 'SELECT legacy_status FROM orders'\n"
        ),
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) >= 1
    assert any(
        e.match_kind
        in (
            DependencyMatchKind.QUALIFIED_REFERENCE,
            DependencyMatchKind.TABLE_AND_COLUMN_CONTEXT,
        )
        for e in evidences
    )


def test_find_identifier_reference() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="orders",
        column="legacy_status",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
        ),
    )
    doc = SourceDocument(
        path="app/constants.py",
        scope=SourceScope.APPLICATION,
        content="DEFAULT_STATUS = legacy_status\n",
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) == 1
    assert evidences[0].line == 1
    assert evidences[0].match_kind is DependencyMatchKind.COLUMN_IDENTIFIER


def test_identifier_boundary_avoids_partial_match() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="orders",
        column="legacy_status",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
        ),
    )
    doc = SourceDocument(
        path="app/service.py",
        scope=SourceScope.APPLICATION,
        content=(
            "legacy_status_backup = 'archived'\n"
            "old_legacy_status_val = 1\n"
        ),
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) == 0


def test_test_scope_is_separate() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="orders",
        column="legacy_status",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
        ),
    )
    app_doc = SourceDocument(
        path="app/order.py",
        scope=SourceScope.APPLICATION,
        content="return order.legacy_status\n",
    )
    test_doc = SourceDocument(
        path="tests/test_order.py",
        scope=SourceScope.TEST,
        content="assert order.legacy_status == 'paid'\n",
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [app_doc, test_doc])

    assert len(evidences) == 2
    app_ev = next(e for e in evidences if e.path == "app/order.py")
    test_ev = next(e for e in evidences if e.path == "tests/test_order.py")
    assert app_ev.source_scope is SourceScope.APPLICATION
    assert test_ev.source_scope is SourceScope.TEST

    summary = summarize_impact([target], evidences)
    assert summary.targets == 1
    assert summary.application_files_with_references == 1
    assert summary.test_files_with_references == 1
    assert summary.qualified_references == 2


def test_excerpt_redaction_applies() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.COLUMN,
        table="users",
        column="token",
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="users",
            column="token",
            sql="ALTER TABLE users DROP COLUMN token;",
        ),
    )
    doc = SourceDocument(
        path="app/auth.py",
        scope=SourceScope.APPLICATION,
        content="SECRET_API_KEY = user.token\n",
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) == 1
    assert evidences[0].excerpt == "[REDACTED]"


def test_match_table_target() -> None:
    target = DependencyTarget(
        type=DependencyTargetType.TABLE,
        table="payments",
        column=None,
        source_change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_TABLE,
            table="payments",
            sql="DROP TABLE payments;",
        ),
    )
    doc = SourceDocument(
        path="app/payment_service.py",
        scope=SourceScope.APPLICATION,
        content=(
            "import models\n"
            "def process_payment(amount):\n"
            "    return models.Payment.charge(amount)\n"
        ),
    )

    analyzer = DependencyAnalyzer()
    evidences = analyzer.analyze([target], [doc])

    assert len(evidences) == 1
    assert evidences[0].line == 3
    assert evidences[0].match_kind is DependencyMatchKind.TABLE_IDENTIFIER
    assert "models.Payment.charge" in evidences[0].excerpt
