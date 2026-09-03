from enum import StrEnum

from pydantic import BaseModel, Field


class SqlOperation(StrEnum):
    CREATE_TABLE = "CREATE_TABLE"
    DROP_TABLE = "DROP_TABLE"
    ADD_COLUMN = "ADD_COLUMN"
    DROP_COLUMN = "DROP_COLUMN"
    ALTER_COLUMN_TYPE = "ALTER_COLUMN_TYPE"
    SET_NOT_NULL = "SET_NOT_NULL"
    DROP_NOT_NULL = "DROP_NOT_NULL"
    SET_DEFAULT = "SET_DEFAULT"
    DROP_DEFAULT = "DROP_DEFAULT"
    ADD_FOREIGN_KEY = "ADD_FOREIGN_KEY"
    CREATE_INDEX = "CREATE_INDEX"
    DROP_INDEX = "DROP_INDEX"


class ColumnDefinition(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    default: str | None = None
    references: str | None = None


class SqlChange(BaseModel):
    statement_index: int = Field(ge=0)
    operation: SqlOperation
    table: str | None = None
    column: str | None = None
    index: str | None = None
    data_type: str | None = None
    nullable: bool | None = None
    default: str | None = None
    references: str | None = None
    columns: list[ColumnDefinition] = Field(default_factory=list)
    index_columns: list[str] = Field(default_factory=list)
    destructive: bool = False
    sql: str
