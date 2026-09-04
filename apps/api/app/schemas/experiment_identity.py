import hashlib
import json
from typing import Any

from app.fixtures.experiment_registry import ControlledExperimentFixture

VERIFIER_CONTRACT_VERSION = "1"


def canonical_sha256(prefix: str, value: Any) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(canonical).hexdigest()}"


def compute_experiment_contract_digest(
    fixture: ControlledExperimentFixture,
    *,
    baseline_schema: str,
    seed_data: str,
) -> str:
    return canonical_sha256(
        "contract",
        {
            "baseline_schema": baseline_schema,
            "seed_data": seed_data,
            "target": fixture.target,
            "template": fixture.template.value,
            "verification_sql": fixture.verification_sql,
            "verifier_contract_version": VERIFIER_CONTRACT_VERSION,
        },
    )


def compute_subject_digest(migration_sql: str, *, variant: str) -> str:
    return canonical_sha256(
        "subject",
        {"candidate_variant": variant, "migration": migration_sql},
    )
