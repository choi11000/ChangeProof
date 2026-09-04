import logging
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.analyzers.experiment_verifier import ExperimentVerifier
from app.executors.api_experiment import ApiExperimentExecutor
from app.executors.performance_experiment import PerformanceExperimentExecutor
from app.executors.postgres_experiment import (
    FixtureExecutionResult,
    PostgresExperimentExecutor,
)
from app.fixtures.api_fixtures import ControlledApiFixture, get_controlled_api_fixture
from app.fixtures.experiment_registry import (
    ControlledExperimentFixture,
    get_controlled_fixture,
    get_repo_root,
)
from app.fixtures.shiftsafe_fixtures import (
    ControlledPerformanceFixture,
    get_controlled_performance_fixture,
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
        executor: PostgresExperimentExecutor | None = None,
        verifier: ExperimentVerifier | None = None,
        api_executor: ApiExperimentExecutor | None = None,
        perf_executor: PerformanceExperimentExecutor | None = None,
        *,
        repo_root: Path | None = None,
    ) -> None:
        self.executor = executor
        self.api_executor = api_executor or ApiExperimentExecutor()
        self.perf_executor = perf_executor or PerformanceExperimentExecutor()
        self.verifier = verifier or ExperimentVerifier()
        self.repo_root = repo_root or get_repo_root()

    def execute(self, request: ExecuteExperimentRequest) -> ExperimentRun:
        # Check Performance / ShiftSafe fixtures first
        perf_fixture = get_controlled_performance_fixture(request.fixture_id)
        if perf_fixture is not None:
            return self.execute_controlled_performance_fixture(
                perf_fixture,
                experiment_plan_id=request.experiment_plan_id,
                variant="candidate",
            )

        api_fixture = get_controlled_api_fixture(request.fixture_id)
        if api_fixture is not None:
            return self.execute_controlled_api_fixture(
                api_fixture,
                experiment_plan_id=request.experiment_plan_id,
                variant="changed",
            )

        fixture = get_controlled_fixture(request.fixture_id)
        if fixture is None:
            raise UnknownFixtureError(
                f"Unknown or uncontrolled experiment fixture: {request.fixture_id!r}. "
                "Execution is strictly restricted to controlled fixtures."
            )

        return self.execute_controlled_fixture(
            fixture,
            experiment_plan_id=request.experiment_plan_id,
            subject_variant="original",
        )

    def execute_controlled_performance_fixture(
        self,
        fixture: ControlledPerformanceFixture,
        *,
        experiment_plan_id: str | None = None,
        variant: str = "candidate",
    ) -> ExperimentRun:
        started_at = datetime.now(UTC)
        step_results = self.perf_executor.execute_fixture(fixture, variant=variant)
        finished_at = datetime.now(UTC)

        verdict, summary = self.verifier.evaluate(fixture.template, step_results)
        plan_id = experiment_plan_id or f"plan_{fixture.id.replace('/', '_')}"

        # Extract aggregate metrics from the load step
        perf_metrics = None
        for step in step_results:
            if step.performance_metrics:
                perf_metrics = step.performance_metrics
                break

        return ExperimentRun(
            id=f"run_perf_{uuid.uuid4().hex[:12]}",
            experiment_plan_id=plan_id,
            experiment_contract_digest=fixture.compute_contract_digest(),
            subject_digest=fixture.compute_subject_digest(variant=variant),
            template=fixture.template,
            domain="PERFORMANCE",
            verdict=verdict,
            started_at=started_at,
            finished_at=finished_at,
            step_results=step_results,
            performance_metrics=perf_metrics,
            cleanup_succeeded=True,
            summary=summary,
        )

    def execute_controlled_api_fixture(
        self,
        fixture: ControlledApiFixture,
        *,
        experiment_plan_id: str | None = None,
        variant: str = "changed",
    ) -> ExperimentRun:
        started_at = datetime.now(UTC)
        step_results = self.api_executor.execute_fixture(fixture, variant=variant)
        finished_at = datetime.now(UTC)

        verdict, summary = self.verifier.evaluate(fixture.template, step_results)
        plan_id = experiment_plan_id or f"plan_{fixture.id.replace('/', '_')}"

        return ExperimentRun(
            id=f"run_api_{uuid.uuid4().hex[:12]}",
            experiment_plan_id=plan_id,
            experiment_contract_digest=fixture.compute_contract_digest(),
            subject_digest=fixture.compute_subject_digest(variant=variant),
            template=fixture.template,
            domain="API",
            verdict=verdict,
            started_at=started_at,
            finished_at=finished_at,
            step_results=step_results,
            cleanup_succeeded=True,
            summary=summary,
        )

    def execute_controlled_fixture(
        self,
        fixture: ControlledExperimentFixture,
        *,
        experiment_plan_id: str | None = None,
        subject_variant: str,
        migration_path: str | None = None,
    ) -> ExperimentRun:
        executable_fixture = (
            replace(fixture, migration_path=migration_path) if migration_path else fixture
        )
        started_at = datetime.now(UTC)
        execution = self.executor.execute_fixture(executable_fixture, repo_root=self.repo_root)
        if isinstance(execution, list):
            execution = FixtureExecutionResult(execution, None)
        finished_at = datetime.now(UTC)

        verdict, summary = self.verifier.evaluate(
            fixture.template,
            execution.step_results,
            expected_sqlstate=fixture.expected_sqlstate,
        )

        plan_id = experiment_plan_id or f"plan_{fixture.id.replace('/', '_')}"
        baseline_schema = fixture.read_baseline_schema(self.repo_root)
        seed_data = fixture.read_seed_data(self.repo_root)
        migration = executable_fixture.read_migration(self.repo_root)
        contract_digest = compute_experiment_contract_digest(
            fixture,
            baseline_schema=baseline_schema,
            seed_data=seed_data,
        )

        run = ExperimentRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            experiment_plan_id=plan_id,
            experiment_contract_digest=contract_digest,
            subject_digest=compute_subject_digest(migration, variant=subject_variant),
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
