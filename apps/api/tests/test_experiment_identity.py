from dataclasses import replace

from app.fixtures.experiment_registry import get_controlled_fixture, get_repo_root
from app.schemas.experiment_identity import (
    compute_experiment_contract_digest,
    compute_subject_digest,
)


def _contract(fixture, *, baseline=None, seed=None):
    root = get_repo_root()
    return compute_experiment_contract_digest(
        fixture,
        baseline_schema=baseline if baseline is not None else fixture.read_baseline_schema(root),
        seed_data=seed if seed is not None else fixture.read_seed_data(root),
    )


def test_same_contract_has_same_digest() -> None:
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None
    assert _contract(fixture) == _contract(fixture)


def test_changed_verification_contract_has_different_digest() -> None:
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None
    changed = replace(fixture, verification_sql="SELECT 1;")
    assert _contract(fixture) != _contract(changed)


def test_changed_baseline_or_seed_changes_contract_digest() -> None:
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None
    assert _contract(fixture) != _contract(fixture, baseline="SELECT 1;")
    assert _contract(fixture) != _contract(fixture, seed="SELECT 1;")


def test_changed_migration_preserves_contract_and_changes_subject() -> None:
    fixture = get_controlled_fixture("risky-saas/drop-legacy-status")
    assert fixture is not None
    original = fixture.read_migration(get_repo_root())
    remediated = original + "\n-- compatibility remediation"
    assert _contract(fixture) == _contract(fixture)
    assert compute_subject_digest(original, variant="original") != compute_subject_digest(
        remediated, variant="remediated"
    )
