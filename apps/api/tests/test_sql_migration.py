from pathlib import Path

import pytest

from app.analyzers.sql_migration import SqlMigrationParseError, SqlMigrationParser
from app.schemas.sql_change import SqlOperation

parser = SqlMigrationParser()


def test_parses_create_table_column_metadata() -> None:
    changes = parser.parse(
        """
        CREATE TABLE users (
            id BIGINT PRIMARY KEY,
            email VARCHAR(255) NOT NULL DEFAULT 'unknown',
            plan_id BIGINT REFERENCES plans(id)
        );
        """
    )

    assert len(changes) == 1
    assert changes[0].operation is SqlOperation.CREATE_TABLE
    assert changes[0].table == "users"
    assert changes[0].columns[1].model_dump() == {
        "name": "email",
        "data_type": "VARCHAR(255)",
        "nullable": False,
        "default": "'unknown'",
        "references": None,
    }
    assert changes[0].columns[2].references == "plans(id)"


def test_parses_alter_table_actions_and_destructive_flags() -> None:
    changes = parser.parse(
        """
        ALTER TABLE orders DROP COLUMN legacy_status;
        ALTER TABLE users ADD COLUMN region TEXT NOT NULL DEFAULT 'unknown';
        ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(30);
        ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
        ALTER TABLE users ALTER COLUMN status SET DEFAULT 'active';
        ALTER TABLE users ALTER COLUMN status DROP DEFAULT;
        ALTER TABLE users ALTER COLUMN phone DROP NOT NULL;
        """
    )

    assert [change.operation for change in changes] == [
        SqlOperation.DROP_COLUMN,
        SqlOperation.ADD_COLUMN,
        SqlOperation.ALTER_COLUMN_TYPE,
        SqlOperation.SET_NOT_NULL,
        SqlOperation.SET_DEFAULT,
        SqlOperation.DROP_DEFAULT,
        SqlOperation.DROP_NOT_NULL,
    ]
    assert changes[0].destructive is True
    assert changes[1].default == "'unknown'"
    assert changes[1].nullable is False
    assert changes[2].data_type == "VARCHAR(30)"


def test_parses_indexes_tables_and_foreign_keys() -> None:
    changes = parser.parse(
        """
        CREATE INDEX idx_users_email ON users(email);
        DROP INDEX idx_users_email;
        ALTER TABLE orders ADD CONSTRAINT fk_user
          FOREIGN KEY (user_id) REFERENCES users(id);
        DROP TABLE payments;
        """
    )

    assert changes[0].operation is SqlOperation.CREATE_INDEX
    assert changes[0].table == "users"
    assert changes[0].index == "idx_users_email"
    assert changes[0].index_columns == ["email"]
    assert changes[1].operation is SqlOperation.DROP_INDEX
    assert changes[1].destructive is True
    assert changes[2].references == "users(id)"
    assert changes[3].operation is SqlOperation.DROP_TABLE
    assert changes[3].destructive is True


def test_parses_synthetic_risky_migrations() -> None:
    sample_root = Path(__file__).parents[3] / "samples" / "risky-saas" / "migrations"

    results = {
        path.name: parser.parse(path.read_text(encoding="utf-8"))
        for path in sample_root.glob("*.sql")
    }

    assert results["001_drop_legacy_status.sql"][0].operation is SqlOperation.DROP_COLUMN
    assert results["002_shrink_email.sql"][0].data_type == "VARCHAR(30)"
    assert results["003_unsafe_not_null.sql"][0].operation is SqlOperation.SET_NOT_NULL
    assert results["004_drop_payments.sql"][0].operation is SqlOperation.DROP_TABLE


def test_empty_and_non_ddl_sql_produce_no_changes() -> None:
    assert parser.parse("  \n") == []
    assert parser.parse("UPDATE users SET active = TRUE;") == []


def test_invalid_sql_has_a_safe_domain_error() -> None:
    with pytest.raises(SqlMigrationParseError, match="Invalid PostgreSQL migration"):
        parser.parse("ALTER TABLE users ALTER COLUMN;")
