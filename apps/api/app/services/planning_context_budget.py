from collections import defaultdict, deque

from app.clients.openai_client import ChangeFactSummary, EvidenceSummary, FailurePlanningContext
from app.schemas.ai import PlanningContextStats
from app.schemas.dependency import ChangeFact, DependencyEvidence, DependencyMatchKind, SourceScope
from app.schemas.github import AnalysisWarning


class PlanningContextBudgeter:
    """Builds a deterministic, transparent and bounded AI planning context."""

    def __init__(
        self,
        *,
        max_changes: int = 50,
        max_evidence: int = 30,
        max_excerpt_chars: int = 240,
        max_warnings: int = 10,
        max_warning_chars: int = 200,
    ) -> None:
        self.max_changes = max_changes
        self.max_evidence = max_evidence
        self.max_excerpt_chars = max_excerpt_chars
        self.max_warnings = max_warnings
        self.max_warning_chars = max_warning_chars

    def build(
        self,
        changes: list[ChangeFact],
        evidence: list[DependencyEvidence],
        warnings: list[AnalysisWarning],
        *,
        head_sha: str,
        scan_complete: bool,
    ) -> FailurePlanningContext:
        chosen_changes = sorted(changes, key=lambda item: item.id)[: self.max_changes]
        chosen_evidence = self._select_evidence(evidence)
        chosen_warnings = sorted(warning.message for warning in warnings)[: self.max_warnings]
        truncated_warnings = [value[: self.max_warning_chars] for value in chosen_warnings]
        truncated = (
            len(changes) > len(chosen_changes)
            or len(evidence) > len(chosen_evidence)
            or len(warnings) > len(truncated_warnings)
            or any(len(item.excerpt) > self.max_excerpt_chars for item in chosen_evidence)
            or any(len(value) > self.max_warning_chars for value in chosen_warnings)
        )
        stats = PlanningContextStats(
            available_changes=len(changes),
            used_changes=len(chosen_changes),
            available_evidence=len(evidence),
            used_evidence=len(chosen_evidence),
            available_warnings=len(warnings),
            used_warnings=len(truncated_warnings),
            truncated=truncated,
        )
        return FailurePlanningContext(
            head_sha=head_sha,
            changes=[
                ChangeFactSummary(
                    id=item.id,
                    operation=item.change.operation.value,
                    table=item.change.table,
                    column=item.change.column,
                )
                for item in chosen_changes
            ],
            evidence=[
                EvidenceSummary(
                    id=item.id,
                    target=self._target_key(item),
                    path=item.path,
                    line=item.line,
                    match_kind=item.match_kind.value,
                    excerpt=item.excerpt[: self.max_excerpt_chars],
                    source_scope=item.source_scope.value,
                    changed_in_pull_request=item.changed_in_pull_request,
                )
                for item in chosen_evidence
            ],
            scan_complete=scan_complete,
            warnings=truncated_warnings,
            context_truncated=truncated,
            stats=stats,
        )

    def _select_evidence(self, evidence: list[DependencyEvidence]) -> list[DependencyEvidence]:
        ranked = sorted(evidence, key=self._rank)
        groups: dict[str, deque[DependencyEvidence]] = defaultdict(deque)
        for item in ranked:
            groups[self._target_key(item)].append(item)
        selected: list[DependencyEvidence] = []
        # First preserve target coverage; then fill remaining slots by global evidence strength.
        for key in sorted(groups):
            if len(selected) >= self.max_evidence:
                break
            selected.append(groups[key].popleft())
        selected_ids = {item.id for item in selected}
        selected.extend(
            item for item in ranked if item.id not in selected_ids
        )
        return selected[: self.max_evidence]

    @staticmethod
    def _target_key(item: DependencyEvidence) -> str:
        return f"{item.target.type.value}:{item.target.table}:{item.target.column or ''}"

    @staticmethod
    def _rank(item: DependencyEvidence) -> tuple[int, int, int, str, int, str]:
        scope = {SourceScope.APPLICATION: 0, SourceScope.TEST: 1}[item.source_scope]
        kind = {
            DependencyMatchKind.QUALIFIED_REFERENCE: 0,
            DependencyMatchKind.TABLE_AND_COLUMN_CONTEXT: 1,
            DependencyMatchKind.TABLE_IDENTIFIER: 2,
            DependencyMatchKind.COLUMN_IDENTIFIER: 3,
        }[item.match_kind]
        return (scope, kind, int(item.changed_in_pull_request), item.path, item.line, item.id)
