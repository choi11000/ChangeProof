from dataclasses import dataclass
from pathlib import Path

from app.schemas.execution import ExperimentVerdict
from app.schemas.experiment import ExperimentTemplate


@dataclass(frozen=True)
class ControlledExperimentFixture:
    id: str
    name: str
    template: ExperimentTemplate
    target: str
    baseline_schema_path: str
    seed_data_path: str
    migration_path: str
    verification_sql: str
    expected_verdict: ExperimentVerdict
    expected_sqlstate: str | None = None

    def read_baseline_schema(self, repo_root: Path) -> str:
        return (repo_root / self.baseline_schema_path).read_text(encoding="utf-8")

    def read_seed_data(self, repo_root: Path) -> str:
        return (repo_root / self.seed_data_path).read_text(encoding="utf-8")

    def read_migration(self, repo_root: Path) -> str:
        return (repo_root / self.migration_path).read_text(encoding="utf-8")


CONTROLLED_FIXTURES: dict[str, ControlledExperimentFixture] = {
    "risky-saas/drop-legacy-status": ControlledExperimentFixture(
        id="risky-saas/drop-legacy-status",
        name="Drop legacy status column referenced in application",
        template=ExperimentTemplate.DROPPED_COLUMN_REFERENCE,
        target="orders.legacy_status",
        baseline_schema_path="samples/risky-saas/schema.sql",
        seed_data_path="samples/risky-saas/seed.sql",
        migration_path="samples/risky-saas/migrations/001_drop_legacy_status.sql",
        verification_sql='SELECT "legacy_status" FROM "orders" LIMIT 1;',
        expected_verdict=ExperimentVerdict.PROVEN_FAIL,
        expected_sqlstate="42703",  # undefined_column
    ),
    "risky-saas/drop-payments": ControlledExperimentFixture(
        id="risky-saas/drop-payments",
        name="Drop payments table referenced in application",
        template=ExperimentTemplate.DROPPED_TABLE_REFERENCE,
        target="payments",
        baseline_schema_path="samples/risky-saas/schema.sql",
        seed_data_path="samples/risky-saas/seed.sql",
        migration_path="samples/risky-saas/migrations/004_drop_payments.sql",
        verification_sql='SELECT 1 FROM "payments" LIMIT 1;',
        expected_verdict=ExperimentVerdict.PROVEN_FAIL,
        expected_sqlstate="42P01",  # undefined_table
    ),
    "risky-saas/set-not-null": ControlledExperimentFixture(
        id="risky-saas/set-not-null",
        name="Set column NOT NULL when existing rows contain NULL",
        template=ExperimentTemplate.NOT_NULL_COMPATIBILITY,
        target="users.phone",
        baseline_schema_path="samples/risky-saas/schema.sql",
        seed_data_path="samples/risky-saas/seed.sql",
        migration_path="samples/risky-saas/migrations/003_unsafe_not_null.sql",
        verification_sql='SELECT COUNT(*) FROM "users" WHERE "phone" IS NULL;',
        expected_verdict=ExperimentVerdict.PROVEN_FAIL,
        expected_sqlstate="23502",  # not_null_violation
    ),
    "risky-saas/shrink-email": ControlledExperimentFixture(
        id="risky-saas/shrink-email",
        name="Shrink column type when existing rows exceed new length",
        template=ExperimentTemplate.ALTER_TYPE_COMPATIBILITY,
        target="users.email",
        baseline_schema_path="samples/risky-saas/schema.sql",
        seed_data_path="samples/risky-saas/seed.sql",
        migration_path="samples/risky-saas/migrations/002_shrink_email.sql",
        verification_sql='SELECT "email" FROM "users" LIMIT 1;',
        expected_verdict=ExperimentVerdict.PROVEN_FAIL,
        expected_sqlstate="22001",  # string_data_right_truncation
    ),
    "risky-saas/safe-additive": ControlledExperimentFixture(
        id="risky-saas/safe-additive",
        name="Add optional column with no existing constraint violations",
        template=ExperimentTemplate.MIGRATION_APPLY,
        target="orders.external_reference",
        baseline_schema_path="samples/risky-saas/schema.sql",
        seed_data_path="samples/risky-saas/seed.sql",
        migration_path="samples/risky-saas/migrations/005_safe_add_external_reference.sql",
        verification_sql='SELECT "external_reference" FROM "orders" LIMIT 1;',
        expected_verdict=ExperimentVerdict.PROVEN_PASS,
        expected_sqlstate=None,
    ),
}


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents, Path.cwd()]:
        if (candidate / "samples" / "risky-saas").is_dir():
            return candidate
    try:
        return Path(__file__).resolve().parents[4]
    except IndexError:
        return Path("/app")


def get_controlled_fixture(fixture_id: str) -> ControlledExperimentFixture | None:
    return CONTROLLED_FIXTURES.get(fixture_id)
