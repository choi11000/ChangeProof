from collections.abc import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.schemas.sql_change import ColumnDefinition, SqlChange, SqlOperation


class SqlMigrationParseError(ValueError):
    """Raised when a migration cannot be parsed as PostgreSQL SQL."""


class SqlMigrationParser:
    """Convert PostgreSQL DDL into typed, deterministic change records."""

    def parse(self, sql: str) -> list[SqlChange]:
        if not sql.strip():
            return []

        try:
            statements = sqlglot.parse(sql, read="postgres")
        except ParseError as error:
            raise SqlMigrationParseError(f"Invalid PostgreSQL migration: {error}") from error

        changes: list[SqlChange] = []
        for index, statement in enumerate(statements):
            changes.extend(self._parse_statement(index, statement))
        return changes

    def _parse_statement(self, index: int, statement: exp.Expression) -> list[SqlChange]:
        if isinstance(statement, exp.Create):
            return self._parse_create(index, statement)
        if isinstance(statement, exp.Alter) and statement.args.get("kind") == "TABLE":
            return self._parse_alter_table(index, statement)
        if isinstance(statement, exp.Drop):
            return self._parse_drop(index, statement)
        return []

    def _parse_create(self, index: int, statement: exp.Create) -> list[SqlChange]:
        kind = statement.args.get("kind")
        if kind == "TABLE":
            schema = statement.this
            if not isinstance(schema, exp.Schema):
                return []
            return [
                SqlChange(
                    statement_index=index,
                    operation=SqlOperation.CREATE_TABLE,
                    table=self._table_name(schema.this),
                    columns=[
                        self._column_definition(column)
                        for column in schema.expressions
                        if isinstance(column, exp.ColumnDef)
                    ],
                    sql=self._sql(statement),
                )
            ]

        if kind == "INDEX" and isinstance(statement.this, exp.Index):
            index_expression = statement.this
            return [
                SqlChange(
                    statement_index=index,
                    operation=SqlOperation.CREATE_INDEX,
                    table=self._table_name(index_expression.args.get("table")),
                    index=index_expression.name,
                    index_columns=[column.name for column in index_expression.find_all(exp.Column)],
                    sql=self._sql(statement),
                )
            ]
        return []

    def _parse_drop(self, index: int, statement: exp.Drop) -> list[SqlChange]:
        kind = statement.args.get("kind")
        if kind == "TABLE":
            return [
                SqlChange(
                    statement_index=index,
                    operation=SqlOperation.DROP_TABLE,
                    table=self._table_name(statement.this),
                    destructive=True,
                    sql=self._sql(statement),
                )
            ]
        if kind == "INDEX":
            return [
                SqlChange(
                    statement_index=index,
                    operation=SqlOperation.DROP_INDEX,
                    index=self._table_name(statement.this),
                    destructive=True,
                    sql=self._sql(statement),
                )
            ]
        return []

    def _parse_alter_table(self, index: int, statement: exp.Alter) -> list[SqlChange]:
        table = self._table_name(statement.this)
        sql = self._sql(statement)
        changes: list[SqlChange] = []
        for action in statement.args.get("actions") or []:
            if isinstance(action, exp.ColumnDef):
                definition = self._column_definition(action)
                changes.append(
                    SqlChange(
                        statement_index=index,
                        operation=SqlOperation.ADD_COLUMN,
                        table=table,
                        column=definition.name,
                        data_type=definition.data_type,
                        nullable=definition.nullable,
                        default=definition.default,
                        references=definition.references,
                        sql=sql,
                    )
                )
            elif isinstance(action, exp.Drop) and action.args.get("kind") == "COLUMN":
                changes.append(
                    SqlChange(
                        statement_index=index,
                        operation=SqlOperation.DROP_COLUMN,
                        table=table,
                        column=action.this.name,
                        destructive=True,
                        sql=sql,
                    )
                )
            elif isinstance(action, exp.AlterColumn):
                changes.append(self._alter_column(index, table, sql, action))
            elif isinstance(action, exp.AddConstraint):
                changes.extend(self._foreign_keys(index, table, sql, action))
        return changes

    def _alter_column(
        self, index: int, table: str | None, sql: str, action: exp.AlterColumn
    ) -> SqlChange:
        common = {
            "statement_index": index,
            "table": table,
            "column": action.this.name,
            "sql": sql,
        }
        if data_type := action.args.get("dtype"):
            return SqlChange(
                operation=SqlOperation.ALTER_COLUMN_TYPE,
                data_type=data_type.sql(dialect="postgres"),
                **common,
            )
        if "allow_null" in action.args:
            nullable = bool(action.args["allow_null"])
            return SqlChange(
                operation=(SqlOperation.DROP_NOT_NULL if nullable else SqlOperation.SET_NOT_NULL),
                nullable=nullable,
                **common,
            )
        if default := action.args.get("default"):
            return SqlChange(
                operation=SqlOperation.SET_DEFAULT,
                default=default.sql(dialect="postgres"),
                **common,
            )
        return SqlChange(operation=SqlOperation.DROP_DEFAULT, **common)

    def _foreign_keys(
        self, index: int, table: str | None, sql: str, action: exp.AddConstraint
    ) -> Iterable[SqlChange]:
        for foreign_key in action.find_all(exp.ForeignKey):
            reference = foreign_key.args.get("reference")
            yield SqlChange(
                statement_index=index,
                operation=SqlOperation.ADD_FOREIGN_KEY,
                table=table,
                column=next(
                    (column.name for column in foreign_key.expressions),
                    None,
                ),
                references=self._reference_name(reference),
                sql=sql,
            )

    def _column_definition(self, column: exp.ColumnDef) -> ColumnDefinition:
        constraints = [constraint.args.get("kind") for constraint in column.constraints]
        not_null = any(isinstance(kind, exp.NotNullColumnConstraint) for kind in constraints)
        default_constraint = next(
            (kind for kind in constraints if isinstance(kind, exp.DefaultColumnConstraint)),
            None,
        )
        reference = next((kind for kind in constraints if isinstance(kind, exp.Reference)), None)
        return ColumnDefinition(
            name=column.name,
            data_type=column.kind.sql(dialect="postgres"),
            nullable=not not_null,
            default=(
                default_constraint.this.sql(dialect="postgres") if default_constraint else None
            ),
            references=self._reference_name(reference),
        )

    @staticmethod
    def _reference_name(reference: exp.Expression | None) -> str | None:
        if not isinstance(reference, exp.Reference):
            return None
        schema = reference.this
        if not isinstance(schema, exp.Schema):
            return None
        table = SqlMigrationParser._table_name(schema.this)
        columns = ",".join(expression.name for expression in schema.expressions)
        return f"{table}({columns})"

    @staticmethod
    def _table_name(expression: exp.Expression | None) -> str | None:
        return expression.name if expression is not None else None

    @staticmethod
    def _sql(statement: exp.Expression) -> str:
        return statement.sql(dialect="postgres")
