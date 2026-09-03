import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.analyzers.experiment_verifier import ExperimentVerifier
from app.executors.postgres_experiment import (
    FixtureExecutionResult,
    PostgresExperimentExecutor,
)
from app.fixtures.experiment_registry import (
    get_controlled_fixture,
    get_repo_root,
)
from app.schemas.execution import (
    ExecuteExperimentRequest,
    ExperimentRun,
)
from app.schemas.experiment_identity import (
    compute_experiment_contract_digest,
    compute_subject_digest,
)

logger = logging.getLogger(__name__)


class UnknownFixtureError(ValueError):
    """Raised when an experiment execution is requested for an uncontrolled fixture."""

    pass


class ExperimentExecutionService:
    """Orchestrates controlled fixture execution and deterministic verdict verification."""

    def __init__(
        self,
        executor: PostgresExperimentExecutor,
        verifier: ExperimentVerifier | None = None,
        *,
        repo_root: Path | None = None,
    ) -> None:
        self.executor = executor
        self.verifier = verifier or ExperimentVerifier()
        self.repo_root = repo_root or get_repo_root()

    def execute(self, request: ExecuteExperimentRequest) -> ExperimentRun:
        fixture = get_controlled_fixture(request.fixture_id)
        if fixture is None:
            raise UnknownFixtureError(
                f"Unknown or uncontrolled experiment fixture: {request.fixture_id!r}. "
                "Execution is strictly restricted to controlled fixtures."
            )

        started_at = datetime.now(UTC)
        execution = self.executor.execute_fixture(fixture, repo_root=self.repo_root)
        if isinstance(execution, list):
            execution = FixtureExecutionResult(execution, None)
        finished_at = datetime.now(UTC)

        verdict, summary = self.verifier.evaluate(
            fixture.template,
            execution.step_results,
            expected_sqlstate=fixture.expected_sqlstate,
        )

        plan_id = request.experiment_plan_id or f"plan_{fixture.id.replace('/', '_')}"
        baseline_schema = fixture.read_baseline_schema(self.repo_root)
        seed_data = fixture.read_seed_data(self.repo_root)
        migration = fixture.read_migration(self.repo_root)
        contract_digest = compute_experiment_contract_digest(
            fixture,
            baseline_schema=baseline_schema,
            seed_data=seed_data,
        )

        run = ExperimentRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            experiment_plan_id=plan_id,
            experiment_contract_digest=contract_digest,
            subject_digest=compute_subject_digest(migration, variant="original"),
            template=fixture.template,
            verdict=verdict,
            started_at=started_at,
            finished_at=finished_at,
            step_results=execution.step_results,
            cleanup_succeeded=execution.cleanup_succeeded,
            summary=summary,
        )

        logger.info(
            "Executed experiment in isolated sandbox",
            extra={
                "fixture_id": fixture.id,
                "template": fixture.template,
                "verdict": verdict,
                "run_id": run.id,
            },
        )
        return run
