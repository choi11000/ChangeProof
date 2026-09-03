import logging

from app.analyzers.experiment_compiler import ExperimentCompiler, ExperimentCompilerError
from app.clients.openai_client import (
    ChangeFactSummary,
    EvidenceSummary,
    FailurePlanningContext,
    HypothesisGenerator,
    OpenAIAuthError,
    OpenAIRateLimitError,
    OpenAIResponseError,
    OpenAITimeoutError,
)
from app.schemas.dependency import ChangeFact, DependencyEvidence
from app.schemas.experiment import ExperimentPlan, ExperimentTemplate
from app.schemas.github import AnalysisStep, AnalysisWarning, AnalysisWarningCode
from app.schemas.hypothesis import FailureHypothesis

logger = logging.getLogger(__name__)

MAX_HYPOTHESES = 3


class FailurePlanningService:
    """Orchestrates evidence-grounded failure hypothesis generation and safe experiment planning."""

    def __init__(
        self,
        generator: HypothesisGenerator | None = None,
        compiler: ExperimentCompiler | None = None,
    ) -> None:
        self.generator = generator
        self.compiler = compiler or ExperimentCompiler()

    async def plan(
        self,
        changes: list[ChangeFact],
        evidence: list[DependencyEvidence],
        *,
        scan_complete: bool = True,
        existing_warnings: list[AnalysisWarning] | None = None,
    ) -> tuple[
        list[FailureHypothesis],
        list[ExperimentPlan],
        list[AnalysisWarning],
        list[AnalysisStep],
    ]:
        warnings: list[AnalysisWarning] = []
        completed_steps: list[AnalysisStep] = []

        if not changes:
            # Nothing changed; no hypothesis to plan
            return [], [], warnings, completed_steps

        if self.generator is None or (
            hasattr(self.generator, "is_configured") and not self.generator.is_configured
        ):
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.AI_NOT_CONFIGURED,
                    message=(
                        "OpenAI API key is not configured; "
                        "AI failure hypothesis planning skipped"
                    ),
                )
            )
            return [], [], warnings, completed_steps

        # 1. Build minimal safe context
        context = FailurePlanningContext(
            changes=[
                ChangeFactSummary(
                    id=c.id,
                    operation=c.change.operation.value,
                    table=c.change.table,
                    column=c.change.column,
                )
                for c in changes
            ],
            evidence=[
                EvidenceSummary(
                    id=e.id,
                    path=e.path,
                    line=e.line,
                    match_kind=e.match_kind.value,
                    excerpt=e.excerpt,
                    changed_in_pull_request=e.changed_in_pull_request,
                )
                for e in evidence
            ],
            scan_complete=scan_complete,
            warnings=[w.message for w in (existing_warnings or [])],
        )

        # 2. Call Hypothesis Generator
        try:
            proposal = await self.generator.generate(context)
            completed_steps.append(AnalysisStep.GENERATE_FAILURE_HYPOTHESES)
        except OpenAIAuthError as exc:
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.AI_NOT_CONFIGURED,
                    message=f"OpenAI authentication error: {exc}",
                )
            )
            return [], [], warnings, completed_steps
        except OpenAIRateLimitError as exc:
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.AI_RATE_LIMITED,
                    message=f"OpenAI rate limit exceeded: {exc}",
                )
            )
            return [], [], warnings, completed_steps
        except (OpenAITimeoutError, OpenAIResponseError) as exc:
            warnings.append(
                AnalysisWarning(
                    code=AnalysisWarningCode.AI_REQUEST_FAILED,
                    message=f"OpenAI hypothesis generation failed: {exc}",
                )
            )
            return [], [], warnings, completed_steps

        # 3. Domain Validation of Generated Hypotheses
        valid_change_ids = {c.id for c in changes}
        valid_evidence_ids = {e.id for e in evidence}
        allowed_templates = set(ExperimentTemplate)

        validated_hypotheses: list[FailureHypothesis] = []
        raw_hypotheses = proposal.hypotheses[:MAX_HYPOTHESES]

        for hyp in raw_hypotheses:
            # Check change_ids subset
            if not hyp.change_ids or not set(hyp.change_ids).issubset(valid_change_ids):
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.AI_OUTPUT_INVALID,
                        message=(
                            f"Hypothesis {hyp.id} referenced unknown change IDs: "
                            f"{set(hyp.change_ids) - valid_change_ids}"
                        ),
                    )
                )
                continue

            # Check evidence_ids subset
            if not set(hyp.evidence_ids).issubset(valid_evidence_ids):
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.AI_OUTPUT_INVALID,
                        message=(
                            f"Hypothesis {hyp.id} referenced unknown evidence IDs: "
                            f"{set(hyp.evidence_ids) - valid_evidence_ids}"
                        ),
                    )
                )
                continue

            # Check template allowlist
            if hyp.experiment_template not in allowed_templates:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.AI_OUTPUT_INVALID,
                        message=(
                            f"Hypothesis {hyp.id} selected disallowed experiment template: "
                            f"{hyp.experiment_template}"
                        ),
                    )
                )
                continue

            validated_hypotheses.append(hyp)

        completed_steps.append(AnalysisStep.VALIDATE_HYPOTHESES)

        # 4. Compile Executable Experiment Plans
        plans: list[ExperimentPlan] = []
        for hyp in validated_hypotheses:
            try:
                plan = self.compiler.compile(hyp, changes, evidence)
                plans.append(plan)
            except ExperimentCompilerError as exc:
                warnings.append(
                    AnalysisWarning(
                        code=AnalysisWarningCode.AI_OUTPUT_INVALID,
                        message=f"Failed to compile plan for hypothesis {hyp.id}: {exc}",
                    )
                )

        if plans:
            completed_steps.append(AnalysisStep.COMPILE_EXPERIMENT_PLANS)

        return validated_hypotheses, plans, warnings, completed_steps
