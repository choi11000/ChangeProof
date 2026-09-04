from pathlib import PurePosixPath

from app.core.redaction import redact_lines
from app.schemas.github import ChangedFile, ClassifiedFile, ContentPolicy, FileCategory

SECRET_NAMES = {"id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".pem", ".key"}
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".exe",
    ".dll",
    ".so",
}
LOCKFILE_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
MIGRATION_SEGMENTS = {"migration", "migrations", "alembic", "versions"}
SCHEMA_SEGMENTS = {"schema", "schemas", "database", "db"}
APPLICATION_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rb"}
CONFIG_NAMES = {
    "dockerfile",
    "compose.yaml",
    "compose.yml",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}


def classify_file(file: ChangedFile) -> ClassifiedFile:
    path = PurePosixPath(file.path.replace("\\", "/"))
    lower_parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    suffix = path.suffix.lower()

    policy = _content_policy(name, lower_parts, suffix)
    safe_file = file.model_copy(update={"patch": _safe_patch(file.patch, policy)})

    if _is_test_path(lower_parts, name):
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.TEST,
            reason="Path or filename matches a test convention",
            content_policy=policy,
        )
    if suffix == ".sql" and any(part in MIGRATION_SEGMENTS for part in lower_parts[:-1]):
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.SQL_MIGRATION,
            reason="File extension is .sql and path contains a migration directory",
            content_policy=policy,
        )
    if suffix == ".sql" and (
        name in {"schema.sql", "structure.sql"}
        or any(part in SCHEMA_SEGMENTS for part in lower_parts[:-1])
    ):
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.DATABASE_SCHEMA,
            reason="SQL file path or filename matches a database schema convention",
            content_policy=policy,
        )
    if name.startswith("readme") or suffix in {".md", ".mdx", ".rst"}:
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.DOCUMENTATION,
            reason="File extension or filename matches documentation",
            content_policy=policy,
        )
    if name in {"openapi.yaml", "openapi.yml", "openapi.json"} or (
        suffix in {".yaml", ".yml", ".json"}
        and any(part in {"openapi", "swagger", "api_spec", "api-spec"} for part in lower_parts)
    ):
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.OPENAPI_SPEC,
            reason="Filename or path matches OpenAPI specification",
            content_policy=policy,
        )
    if name in CONFIG_NAMES or suffix in {".toml", ".yaml", ".yml", ".json", ".ini"}:
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.CONFIG,
            reason="Filename or extension matches configuration",
            content_policy=policy,
        )
    if suffix in APPLICATION_SUFFIXES:
        return ClassifiedFile(
            file=safe_file,
            category=FileCategory.APPLICATION,
            reason="File extension matches supported application source",
            content_policy=policy,
        )
    return ClassifiedFile(
        file=safe_file,
        category=FileCategory.OTHER,
        reason="No deterministic classification rule matched",
        content_policy=policy,
    )


def _content_policy(name: str, parts: tuple[str, ...], suffix: str) -> ContentPolicy:
    if (
        name == ".env"
        or name.startswith(".env.")
        or name in SECRET_NAMES
        or suffix in SECRET_SUFFIXES
    ):
        return ContentPolicy.SKIP_SECRET
    if suffix in BINARY_SUFFIXES:
        return ContentPolicy.SKIP_BINARY
    if name in LOCKFILE_NAMES:
        return ContentPolicy.SKIP_LARGE_LOCKFILE
    return ContentPolicy.ALLOW


def _is_test_path(parts: tuple[str, ...], name: str) -> bool:
    return (
        any(part in {"test", "tests", "fixtures", "__tests__"} for part in parts[:-1])
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    )


def _safe_patch(patch: str | None, policy: ContentPolicy) -> str | None:
    if patch is None or policy is not ContentPolicy.ALLOW:
        return None
    return redact_lines(patch, preserve_diff_prefix=True)
