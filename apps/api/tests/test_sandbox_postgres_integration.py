import psycopg
import pytest

from app.core.config import get_settings
from app.executors.postgres_experiment import PostgresExperimentExecutor
from app.schemas.execution import ExecuteExperimentRequest, ExperimentVerdict
from app.services.experiment_execution_service import ExperimentExecutionService


def is_sandbox_available() -> bool:
    settings = get_settings()
    url = settings.sandbox_database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        conn = psycopg.connect(url, connect_timeout=1)
        conn.close()
        return True
    except Exception:
        return False


sandbox_available = is_sandbox_available()


@pytest.mark.sandbox
class TestSandboxPostgresIntegration:
    @pytest.fixture(autouse=True)
    def check_sandbox(self):
        if not sandbox_available:
            pytest.skip(
                "Sandbox PostgreSQL is not running on localhost:5433. "
                "Start with 'docker compose --profile sandbox up -d sandbox-postgres'"
            )

    def test_real_sandbox_drop_column_proven_fail(self):
        settings = get_settings()
        executor = PostgresExperimentExecutor(settings.sandbox_database_url)
        service = ExperimentExecutionService(executor)

        run = service.execute(
            ExecuteExperimentRequest(fixture_id="risky-saas/drop-legacy-status")
        )
        assert run.verdict is ExperimentVerdict.PROVEN_FAIL
        assert "42703" in run.summary

        # Check evidence structure
        query_step = next(s for s in run.step_results if s.type == "RUN_READ_QUERY")
        assert query_step.status == "FAILED"
        assert query_step.sql_state == "42703"
        assert "changeproof" not in (query_step.message or "")

    def test_real_sandbox_drop_table_proven_fail(self):
        settings = get_settings()
        executor = PostgresExperimentExecutor(settings.sandbox_database_url)
        service = ExperimentExecutionService(executor)

        run = service.execute(
            ExecuteExperimentRequest(fixture_id="risky-saas/drop-payments")
        )
        assert run.verdict is ExperimentVerdict.PROVEN_FAIL
        assert "42P01" in run.summary

    def test_real_sandbox_set_not_null_proven_fail(self):
        settings = get_settings()
        executor = PostgresExperimentExecutor(settings.sandbox_database_url)
        service = ExperimentExecutionService(executor)

        run = service.execute(
            ExecuteExperimentRequest(fixture_id="risky-saas/set-not-null")
        )
        assert run.verdict is ExperimentVerdict.PROVEN_FAIL
        assert "23502" in run.summary

    def test_real_sandbox_shrink_email_proven_fail(self):
        settings = get_settings()
        executor = PostgresExperimentExecutor(settings.sandbox_database_url)
        service = ExperimentExecutionService(executor)

        run = service.execute(
            ExecuteExperimentRequest(fixture_id="risky-saas/shrink-email")
        )
        assert run.verdict is ExperimentVerdict.PROVEN_FAIL
        assert "22001" in run.summary

    def test_real_sandbox_safe_additive_proven_pass(self):
        settings = get_settings()
        executor = PostgresExperimentExecutor(settings.sandbox_database_url)
        service = ExperimentExecutionService(executor)

        run = service.execute(
            ExecuteExperimentRequest(fixture_id="risky-saas/safe-additive")
        )
        assert run.verdict is ExperimentVerdict.PROVEN_PASS
        assert all(s.status == "PASSED" for s in run.step_results)
