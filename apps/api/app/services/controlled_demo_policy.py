from dataclasses import dataclass

from app.core.config import Settings
from app.schemas.dependency import ChangeFact
from app.schemas.github import GitHubRepositoryRef, PullRequestMetadata
from app.schemas.sql_change import SqlOperation


@dataclass(frozen=True)
class ControlledDemoDecision:
    allowed: bool
    fixture_id: str | None = None
    notice: str | None = None


class ControlledDemoPolicy:
    """Enforces exact identity matching for sandbox execution authorization.

    Replaces substring-based matching to eliminate security risks of executing
    arbitrary or attacker-controlled repositories.
    """

    def __init__(self, settings: Settings) -> None:
        self._demo_repo = (settings.controlled_demo_repository or "").strip().lower()
        self._demo_pr = settings.controlled_demo_pr
        self._demo_sha = (settings.controlled_demo_head_sha or "").strip().lower()

    def evaluate(
        self,
        repository: GitHubRepositoryRef,
        metadata: PullRequestMetadata,
        change_facts: list[ChangeFact],
    ) -> ControlledDemoDecision:
        # If no server demo identity is configured, sandbox execution is disabled
        if not self._demo_repo or self._demo_pr is None or not self._demo_sha:
            return ControlledDemoDecision(
                allowed=False,
                notice="Sandbox execution is limited to controlled demo fixtures in this MVP.",
            )

        repo_full_name = repository.full_name.strip().lower()
        if repo_full_name != self._demo_repo:
            return ControlledDemoDecision(
                allowed=False,
                notice="Sandbox execution is limited to controlled demo fixtures in this MVP.",
            )

        if metadata.number != self._demo_pr:
            return ControlledDemoDecision(
                allowed=False,
                notice=(
                    f"Sandbox execution is limited to the audited demo pull request "
                    f"#{self._demo_pr}."
                ),
            )

        actual_sha = metadata.head_sha.strip().lower()
        if actual_sha != self._demo_sha:
            return ControlledDemoDecision(
                allowed=False,
                notice=(
                    "Sandbox execution is disabled because this demo revision is not "
                    "the audited revision."
                ),
            )

        # Exact repository, PR number, and head SHA matched.
        # Now map to recognized controlled fixture:
        for cf in change_facts:
            ch = cf.change
            if ch.table == "orders" and ch.column == "legacy_status":
                return ControlledDemoDecision(
                    allowed=True,
                    fixture_id="risky-saas/drop-legacy-status",
                )
            if ch.table == "payments" and ch.operation == SqlOperation.DROP_TABLE:
                return ControlledDemoDecision(
                    allowed=True,
                    fixture_id="risky-saas/drop-payments",
                )
            if ch.table == "users" and ch.column == "phone":
                return ControlledDemoDecision(
                    allowed=True,
                    fixture_id="risky-saas/set-not-null",
                )
            if ch.table == "users" and ch.column == "email":
                return ControlledDemoDecision(
                    allowed=True,
                    fixture_id="risky-saas/shrink-email",
                )
            if ch.table == "orders" and ch.column == "external_reference":
                return ControlledDemoDecision(
                    allowed=True,
                    fixture_id="risky-saas/safe-additive",
                )

        return ControlledDemoDecision(
            allowed=False,
            notice=(
                "Sandbox execution is disabled: Changes in this demo PR do not map "
                "to any registered controlled fixture."
            ),
        )
