from app.core.config import Settings
from app.schemas.dependency import ChangeFact
from app.schemas.github import GitHubRepositoryRef, PullRequestMetadata
from app.schemas.sql_change import SqlChange, SqlOperation
from app.services.controlled_demo_policy import ControlledDemoPolicy


def _make_settings(
    repo: str = "choi11000/changeproof-demo",
    pr: int = 1,
    sha: str = "08302ccf5e67d12eee0d6470ac1136f4f644cba5",
) -> Settings:
    return Settings(
        controlled_demo_repository=repo,
        controlled_demo_pr=pr,
        controlled_demo_head_sha=sha,
    )


def _make_meta(
    repo: str = "choi11000/changeproof-demo",
    number: int = 1,
    sha: str = "08302ccf5e67d12eee0d6470ac1136f4f644cba5",
) -> PullRequestMetadata:
    return PullRequestMetadata(
        repository=repo,
        number=number,
        title="Demo PR",
        state="open",
        base_branch="main",
        head_branch="demo/drop-legacy-status",
        base_sha="base_sha_123",
        head_sha=sha,
        changed_files=1,
        html_url=f"https://github.com/{repo}/pull/{number}",
    )


def _drop_column_fact() -> ChangeFact:
    return ChangeFact(
        id="cf_1",
        sql_file_path="migrations/001.sql",
        statement_index=0,
        change=SqlChange(
            statement_index=0,
            operation=SqlOperation.DROP_COLUMN,
            table="orders",
            column="legacy_status",
            sql="ALTER TABLE orders DROP COLUMN legacy_status;",
            destructive=True,
        ),
    )


def test_exact_demo_identity_allowed() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-demo")
    meta = _make_meta()
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is True
    assert decision.fixture_id == "risky-saas/drop-legacy-status"
    assert decision.notice is None


def test_same_repo_different_pr_denied() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-demo")
    meta = _make_meta(number=99)
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None
    assert "limited to the audited demo pull request #1" in decision.notice


def test_same_pr_different_sha_denied() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-demo")
    meta = _make_meta(sha="unapproved_different_sha_999")
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None
    assert "not the audited revision" in decision.notice


def test_evil_risky_saas_substring_denied() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    # Substring matching would have previously allowed this!
    repo = GitHubRepositoryRef(owner="attacker", repo="evil-risky-saas")
    meta = _make_meta(repo="attacker/evil-risky-saas")
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None
    assert "limited to controlled demo fixtures" in decision.notice


def test_different_owner_same_repo_name_denied() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="other-user", repo="changeproof-demo")
    meta = _make_meta(repo="other-user/changeproof-demo")
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None


def test_generic_public_repo_denied() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="facebook", repo="react")
    meta = _make_meta(repo="facebook/react", number=123, sha="some_sha")
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None
    assert "limited to controlled demo fixtures" in decision.notice


def test_case_insensitive_normalization_allowed() -> None:
    settings = _make_settings()
    policy = ControlledDemoPolicy(settings)

    # Mixed casing should normalize cleanly per GitHub semantics
    repo = GitHubRepositoryRef(owner="Choi11000", repo="ChangeProof-Demo")
    meta = _make_meta(
        repo="Choi11000/ChangeProof-Demo",
        sha="08302CCF5E67D12EEE0D6470AC1136F4F644CBA5",
    )
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is True
    assert decision.fixture_id == "risky-saas/drop-legacy-status"


def test_demo_identity_unconfigured_denied() -> None:
    settings = Settings(
        controlled_demo_repository=None,
        controlled_demo_pr=None,
        controlled_demo_head_sha=None,
    )
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-demo")
    meta = _make_meta()
    decision = policy.evaluate(repo, meta, [_drop_column_fact()])

    assert decision.allowed is False
    assert decision.fixture_id is None


def _api_change_fact() -> ChangeFact:
    from app.schemas.api_contract import ApiChange, ApiChangeType
    return ChangeFact(
        id="cf_api_1",
        domain="API",
        api_change=ApiChange(
            change_type=ApiChangeType.REMOVE_RESPONSE_FIELD,
            method="GET",
            path="/users/{id}",
            status_code=200,
            media_type="application/json",
            field_name="email",
            schema_name="User",
            json_pointer="#/components/schemas/User/properties/email",
            destructive=True,
            spec_file_path="openapi.yaml",
        ),
    )


def test_api_demo_exact_identity_allowed() -> None:
    settings = Settings(
        controlled_demo_repository="choi11000/changeproof-demo",
        controlled_demo_pr=1,
        controlled_demo_head_sha="08302ccf5e67d12eee0d6470ac1136f4f644cba5",
        controlled_api_demo_repository="choi11000/changeproof-api-demo",
        controlled_api_demo_pr=1,
        controlled_api_demo_head_sha="api_head_sha_12345",
    )
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-api-demo")
    meta = PullRequestMetadata(
        repository="choi11000/changeproof-api-demo",
        number=1,
        title="Demo API PR",
        state="open",
        base_branch="main",
        head_branch="demo/remove-user-email",
        base_sha="base_sha_456",
        head_sha="api_head_sha_12345",
        changed_files=1,
        html_url="https://github.com/choi11000/changeproof-api-demo/pull/1",
    )
    decision = policy.evaluate(repo, meta, [_api_change_fact()])

    assert decision.allowed is True
    assert decision.fixture_id == "api-contract/remove-user-email"


def test_api_demo_wrong_pr_or_sha_denied() -> None:
    settings = Settings(
        controlled_api_demo_repository="choi11000/changeproof-api-demo",
        controlled_api_demo_pr=1,
        controlled_api_demo_head_sha="api_head_sha_12345",
    )
    policy = ControlledDemoPolicy(settings)

    repo = GitHubRepositoryRef(owner="choi11000", repo="changeproof-api-demo")
    meta_wrong_pr = PullRequestMetadata(
        repository="choi11000/changeproof-api-demo",
        number=99,
        title="Demo API PR",
        state="open",
        base_branch="main",
        head_branch="demo/remove-user-email",
        base_sha="base_sha_456",
        head_sha="api_head_sha_12345",
        changed_files=1,
        html_url="https://github.com/choi11000/changeproof-api-demo/pull/99",
    )
    decision = policy.evaluate(repo, meta_wrong_pr, [_api_change_fact()])
    assert decision.allowed is False
    assert "limited to the audited demo pull request #1" in decision.notice

    meta_wrong_sha = PullRequestMetadata(
        repository="choi11000/changeproof-api-demo",
        number=1,
        title="Demo API PR",
        state="open",
        base_branch="main",
        head_branch="demo/remove-user-email",
        base_sha="base_sha_456",
        head_sha="wrong_sha",
        changed_files=1,
        html_url="https://github.com/choi11000/changeproof-api-demo/pull/1",
    )
    decision2 = policy.evaluate(repo, meta_wrong_sha, [_api_change_fact()])
    assert decision2.allowed is False
    assert "not the audited revision" in decision2.notice
