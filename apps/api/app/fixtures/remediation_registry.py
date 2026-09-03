from dataclasses import dataclass

from app.schemas.remediation import RemediationStrategy


@dataclass(frozen=True)
class ControlledRemediation:
    id: str
    experiment_fixture_id: str
    strategy: RemediationStrategy
    description: str
    remediated_migration_path: str


CONTROLLED_REMEDIATIONS: dict[str, ControlledRemediation] = {
    "risky-saas/drop-legacy-status": ControlledRemediation(
        id="remediation/risky-saas/preserve-legacy-status",
        experiment_fixture_id="risky-saas/drop-legacy-status",
        strategy=RemediationStrategy.PRESERVE_COLUMN_COMPATIBILITY,
        description="Preserve legacy_status during the compatibility window while adding status.",
        remediated_migration_path=(
            "samples/risky-saas/remediations/001_preserve_legacy_status.sql"
        ),
    ),
    "risky-saas/drop-payments": ControlledRemediation(
        id="remediation/risky-saas/preserve-payments-view",
        experiment_fixture_id="risky-saas/drop-payments",
        strategy=RemediationStrategy.PRESERVE_TABLE_COMPATIBILITY,
        description="Rename the table and expose a compatibility view for stale readers.",
        remediated_migration_path=(
            "samples/risky-saas/remediations/004_preserve_payments_view.sql"
        ),
    ),
    "risky-saas/set-not-null": ControlledRemediation(
        id="remediation/risky-saas/backfill-phone",
        experiment_fixture_id="risky-saas/set-not-null",
        strategy=RemediationStrategy.BACKFILL_BEFORE_NOT_NULL,
        description="Backfill synthetic NULL phone values before applying NOT NULL.",
        remediated_migration_path=(
            "samples/risky-saas/remediations/003_backfill_phone_not_null.sql"
        ),
    ),
    "risky-saas/shrink-email": ControlledRemediation(
        id="remediation/risky-saas/normalize-email",
        experiment_fixture_id="risky-saas/shrink-email",
        strategy=RemediationStrategy.NORMALIZE_BEFORE_TYPE_CHANGE,
        description=(
            "Normalize synthetic email data to 30 characters before narrowing the type; "
            "this controlled remediation changes data."
        ),
        remediated_migration_path=(
            "samples/risky-saas/remediations/002_normalize_email.sql"
        ),
    ),
}


def get_controlled_remediation(fixture_id: str) -> ControlledRemediation | None:
    return CONTROLLED_REMEDIATIONS.get(fixture_id)
