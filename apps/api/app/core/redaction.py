import re

from app.schemas.sql_change import SqlChange

SECRET_PATTERN = re.compile(
    r"API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE_KEY|AWS_ACCESS_KEY|OPENAI_API_KEY|GITHUB_TOKEN",
    re.IGNORECASE,
)


def redact_lines(value: str, *, preserve_diff_prefix: bool = False) -> str:
    return "\n".join(
        _redact_line(line, preserve_diff_prefix) if SECRET_PATTERN.search(line) else line
        for line in value.splitlines()
    )


def redact_sql_change(change: SqlChange) -> SqlChange:
    if not SECRET_PATTERN.search(change.sql):
        return change
    return change.model_copy(
        update={
            "sql": "[REDACTED]",
            "default": "[REDACTED]" if change.default is not None else None,
            "columns": [
                column.model_copy(
                    update={
                        "default": "[REDACTED]" if column.default is not None else None,
                    }
                )
                for column in change.columns
            ],
        }
    )


def _redact_line(line: str, preserve_diff_prefix: bool) -> str:
    prefix = line[:1] if preserve_diff_prefix and line[:1] in {"+", "-", " "} else ""
    return f"{prefix}[REDACTED]"
