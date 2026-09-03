import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.analyzers.experiment_verifier import ExperimentVerifier
from app.executors.postgres_experiment import PostgresExperimentExecutor
from app.fixtures.experiment_registry import (
    get_controlled_fixture,
    get_repo_root,
)
from app.schemas.execution import (
    ExecuteExperimentRequest,
    ExperimentRun,
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
        step_results = self.executor.execute_fixture(fixture, repo_root=self.repo_root)
        finished_at = datetime.now(UTC)

        verdict, summary = self.verifier.evaluate(
            fixture.template,
            step_results,
            expected_sqlstate=fixture.expected_sqlstate,
        )

        plan_id = request.experiment_plan_id or f"plan_{fixture.id.replace('/', '_')}"
        raw_digest = f"{fixture.id}:{fixture.template}:{fixture.target}"
        plan_digest = (
            request.plan_digest
            or hashlib.sha256(raw_digest.encode("utf-8")).hexdigest()[:16]
        )

        run = ExperimentRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            experiment_plan_id=plan_id,
            plan_digest=plan_digest,
            template=fixture.template,
            verdict=verdict,
            started_at=started_at,
            finished_at=finished_at,
            step_results=step_results,
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
