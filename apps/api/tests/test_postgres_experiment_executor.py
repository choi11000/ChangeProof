from app.executors.postgres_experiment import PostgresExperimentExecutor
from app.fixtures.experiment_registry import get_controlled_fixture
from app.schemas.execution import ExperimentStepStatus
from app.schemas.experiment import ExperimentStepType


class MockCursor:
    def __init__(self, fetch_result=None, side_effects=None):
        self.fetch_result = fetch_result
        self.side_effects = side_effects or {}
        self.executed_queries: list[str] = []

    def execute(self, query, params=None):
        self.executed_queries.append(query)
        for pattern, exc in self.side_effects.items():
            if pattern in query:
                raise exc

    def fetchone(self):
        return self.fetch_result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    def __init__(self, cursor_factory):
        self.cursor_factory = cursor_factory
        self.closed = False

    def cursor(self):
        return self.cursor_factory()

    def close(self):
        self.closed = True


def test_executor_successful_dropped_column_run() -> None:
    executed: list[str] = []

    def make_cursor():
        cur = MockCursor(fetch_result=("fulfilled",))
        cur.executed_queries = executed
        return cur

    mock_conn = MockConnection(make_cursor)
    executor = PostgresExperimentExecutor(
        "postgresql://test:test@localhost:5433/test",
        connect_factory=lambda *a, **kw: mock_conn,
    )
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None

    results = executor.execute_fixture(fixture)
    assert len(results) == 6
    assert all(r.status is ExperimentStepStatus.PASSED for r in results)
    assert mock_conn.closed is True
    assert any("CREATE SCHEMA" in q for q in executed)
    assert any("DROP SCHEMA" in q and "CASCADE" in q for q in executed)


def test_executor_handles_query_failure_with_sqlstate() -> None:
    query_error = Exception('column "legacy_status" does not exist')
    query_error.sqlstate = "42703"

    def make_cursor():
        return MockCursor(
            side_effects={
                'SELECT "legacy_status"': query_error,
            }
        )

    mock_conn = MockConnection(make_cursor)
    executor = PostgresExperimentExecutor(
        "postgresql://test:test@localhost:5433/test",
        connect_factory=lambda *a, **kw: mock_conn,
    )
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None

    results = executor.execute_fixture(fixture)
    assert len(results) == 6

    step4 = next(s for s in results if s.type is ExperimentStepType.APPLY_MIGRATION)
    assert step4.status is ExperimentStepStatus.PASSED

    step5 = next(s for s in results if s.type is ExperimentStepType.RUN_READ_QUERY)
    assert step5.status is ExperimentStepStatus.FAILED
    assert step5.sql_state == "42703"
    assert "legacy_status" in (step5.message or "")


def test_executor_handles_migration_failure_and_skips_query() -> None:
    mig_error = Exception('column "phone" of relation "users" contains null values')
    mig_error.sqlstate = "23502"

    def make_cursor():
        return MockCursor(
            side_effects={
                "ALTER TABLE users ALTER COLUMN phone SET NOT NULL": mig_error,
            }
        )

    mock_conn = MockConnection(make_cursor)
    executor = PostgresExperimentExecutor(
        "postgresql://test:test@localhost:5433/test",
        connect_factory=lambda *a, **kw: mock_conn,
    )
    fixture = get_controlled_fixture("risky-saas/set-not-null")
    assert fixture is not None

    results = executor.execute_fixture(fixture)
    step4 = next(s for s in results if s.type is ExperimentStepType.APPLY_MIGRATION)
    assert step4.status is ExperimentStepStatus.FAILED
    assert step4.sql_state == "23502"

    step5 = next(s for s in results if s.type is ExperimentStepType.RUN_READ_QUERY)
    assert step5.status is ExperimentStepStatus.SKIPPED


def test_executor_redacts_credentials_in_connection_failure() -> None:
    def fail_connect(*a, **kw):
        raise Exception(
            "connection to server at postgresql://user:supersecretpass@localhost:5433 failed"
        )

    executor = PostgresExperimentExecutor(
        "postgresql://user:supersecretpass@localhost:5433/test",
        connect_factory=fail_connect,
    )
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None

    results = executor.execute_fixture(fixture)
    step1 = next(s for s in results if s.type is ExperimentStepType.PREPARE_DATABASE)
    assert step1.status is ExperimentStepStatus.FAILED
    assert "supersecretpass" not in (step1.message or "")
    assert "[REDACTED]" in (step1.message or "")
    assert len(results) == 6
    assert all(r.status is ExperimentStepStatus.SKIPPED for r in results[1:])
