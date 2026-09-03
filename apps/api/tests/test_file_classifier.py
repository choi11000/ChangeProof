import pytest

from app.analyzers.file_classifier import classify_file
from app.schemas.github import (
    ChangedFile,
    ChangedFileStatus,
    ContentPolicy,
    FileCategory,
)


def changed_file(path: str) -> ChangedFile:
    return ChangedFile(
        path=path,
        status=ChangedFileStatus.MODIFIED,
        additions=1,
        deletions=1,
        changes=2,
    )


@pytest.mark.parametrize(
    ("path", "category"),
    [
        ("db/migrations/001_users.sql", FileCategory.SQL_MIGRATION),
        ("migrations/20260903_orders.sql", FileCategory.SQL_MIGRATION),
        ("database/migrations/add_payment.sql", FileCategory.SQL_MIGRATION),
        ("schema.sql", FileCategory.DATABASE_SCHEMA),
        ("database/current.sql", FileCategory.DATABASE_SCHEMA),
        ("app/service.py", FileCategory.APPLICATION),
        ("src/page.tsx", FileCategory.APPLICATION),
        ("tests/fixtures/search.sql", FileCategory.TEST),
        ("src/page.test.tsx", FileCategory.TEST),
        ("README.md", FileCategory.DOCUMENTATION),
        ("docs/guide.mdx", FileCategory.DOCUMENTATION),
        ("compose.yaml", FileCategory.CONFIG),
        ("pyproject.toml", FileCategory.CONFIG),
        ("queries/monthly_report.sql", FileCategory.OTHER),
        ("examples/query.sql", FileCategory.OTHER),
        ("assets/data.csv", FileCategory.OTHER),
    ],
)
def test_classifies_changed_files(path: str, category: FileCategory) -> None:
    result = classify_file(changed_file(path))

    assert result.category is category
    assert result.reason


@pytest.mark.parametrize(
    ("path", "policy"),
    [
        (".env.production", ContentPolicy.SKIP_SECRET),
        ("certs/server.pem", ContentPolicy.SKIP_SECRET),
        ("id_rsa", ContentPolicy.SKIP_SECRET),
        ("assets/logo.png", ContentPolicy.SKIP_BINARY),
        ("package-lock.json", ContentPolicy.SKIP_LARGE_LOCKFILE),
        ("app/main.py", ContentPolicy.ALLOW),
    ],
)
def test_assigns_safe_content_policy(path: str, policy: ContentPolicy) -> None:
    assert classify_file(changed_file(path)).content_policy is policy


def test_renamed_file_uses_new_path_and_preserves_previous_path() -> None:
    file = changed_file("db/migrations/001_users.sql")
    file.status = ChangedFileStatus.RENAMED
    file.previous_path = "queries/001_users.sql"

    result = classify_file(file)

    assert result.category is FileCategory.SQL_MIGRATION
    assert result.file.previous_path == "queries/001_users.sql"


def test_redacts_secret_bearing_patch_lines() -> None:
    file = changed_file("config/settings.py")
    file.patch = "@@ -1 +1 @@\n-GITHUB_TOKEN=old\n+GITHUB_TOKEN=new\n+SAFE=value"

    result = classify_file(file)

    assert result.file.patch == "@@ -1 +1 @@\n-[REDACTED]\n+[REDACTED]\n+SAFE=value"
    assert "old" not in result.file.patch


def test_removes_patch_for_secret_or_binary_files() -> None:
    secret = changed_file(".env")
    secret.patch = "+PASSWORD=do-not-return"
    binary = changed_file("assets/logo.png")
    binary.patch = "binary detail"

    assert classify_file(secret).file.patch is None
    assert classify_file(binary).file.patch is None
