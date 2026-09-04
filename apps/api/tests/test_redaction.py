from app.analyzers.sql_migration import SqlMigrationParser
from app.core.redaction import redact_lines, redact_sql_change


def test_redacts_secret_lines_without_echoing_values() -> None:
    value = "SAFE=value\nGITHUB_TOKEN=real-value\nPASSWORD=another-value"

    result = redact_lines(value)

    assert result == "SAFE=value\n[REDACTED]\n[REDACTED]"
    assert "real-value" not in result


def test_redacts_secret_bearing_sql_and_default() -> None:
    change = SqlMigrationParser().parse(
        "ALTER TABLE settings ADD COLUMN github_token TEXT DEFAULT 'sensitive-value';"
    )[0]

    result = redact_sql_change(change)

    assert result.sql == "[REDACTED]"
    assert result.default == "[REDACTED]"
    assert "sensitive-value" not in result.model_dump_json()


def test_non_secret_sql_is_unchanged() -> None:
    change = SqlMigrationParser().parse("ALTER TABLE users ADD COLUMN region TEXT;")[0]

    assert redact_sql_change(change) is change
