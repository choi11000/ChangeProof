import logging
import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import psycopg

from app.core.redaction import redact_secrets
from app.fixtures.experiment_registry import ControlledExperimentFixture, get_repo_root
from app.schemas.execution import (
    ExperimentStepResult,
    ExperimentStepStatus,
)
from app.schemas.experiment import ExperimentStepType

logger = logging.getLogger(__name__)

SCHEMA_REGEX = re.compile(r"^[a-z0-9_]+$")


class PostgresExperimentExecutorError(Exception):
    """Raised when an infrastructure error prevents execution."""

    pass


class PostgresExperimentExecutor:
    """Executes controlled experiment fixtures inside isolated PostgreSQL schemas."""

    def __init__(
        self,
        database_url: str,
        *,
        connect_timeout: int = 5,
        statement_timeout_ms: int = 10000,
        lock_timeout_ms: int = 5000,
        connect_factory: Callable[..., psycopg.Connection] | None = None,
    ) -> None:
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://")
        self.connect_timeout = connect_timeout
        self.statement_timeout_ms = statement_timeout_ms
        self.lock_timeout_ms = lock_timeout_ms
        self._connect_factory = connect_factory or psycopg.connect

    def execute_fixture(
        self,
        fixture: ControlledExperimentFixture,
        *,
        repo_root: Path | None = None,
    ) -> list[ExperimentStepResult]:
        root = repo_root or get_repo_root()
        schema_name = f"cp_run_{uuid.uuid4().hex[:12]}"
        if not SCHEMA_REGEX.match(schema_name):
            raise PostgresExperimentExecutorError(f"Invalid schema name: {schema_name}")

        step_results: list[ExperimentStepResult] = []
        conn: psycopg.Connection | None = None

        # 1. PREPARE_DATABASE
        t0 = time.monotonic()
        try:
            conn = self._connect_factory(
                self.database_url,
                connect_timeout=self.connect_timeout,
                autocommit=True,
            )
            with conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA "{schema_name}";')
                cur.execute(f'SET search_path = "{schema_name}", public;')
                cur.execute(f"SET statement_timeout = '{self.statement_timeout_ms}ms';")
                cur.execute(f"SET lock_timeout = '{self.lock_timeout_ms}ms';")

            duration = int((time.monotonic() - t0) * 1000)
            step_results.append(
                ExperimentStepResult(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    status=ExperimentStepStatus.PASSED,
                    duration_ms=duration,
                    message=f"Prepared isolated schema {schema_name}",
                )
            )
        except Exception as exc:
            duration = int((time.monotonic() - t0) * 1000)
            sqlstate = getattr(exc, "sqlstate", None)
            step_results.append(
                ExperimentStepResult(
                    order=1,
                    type=ExperimentStepType.PREPARE_DATABASE,
                    status=ExperimentStepStatus.FAILED,
                    duration_ms=duration,
                    sql_state=sqlstate,
                    error_type=type(exc).__name__,
                    message=redact_secrets(str(exc)),
                )
            )
            # Cannot proceed if database preparation failed
            for order, stype, desc in [
                (2, ExperimentStepType.LOAD_BASELINE_SCHEMA, "Load baseline schema"),
                (3, ExperimentStepType.LOAD_SEED_DATA, "Load seed data"),
                (4, ExperimentStepType.APPLY_MIGRATION, "Apply migration"),
                (5, ExperimentStepType.RUN_READ_QUERY, "Run verification query"),
                (6, ExperimentStepType.CAPTURE_RESULT, "Capture database response"),
            ]:
                step_results.append(
                    ExperimentStepResult(
                        order=order,
                        type=stype,
                        status=ExperimentStepStatus.SKIPPED,
                        duration_ms=0,
                        message=f"Skipped: {desc} (database preparation failed)",
                    )
                )
            return step_results

        try:
            # 2. LOAD_BASELINE_SCHEMA
            baseline_sql = fixture.read_baseline_schema(root)
            t_baseline = time.monotonic()
            try:
                with conn.cursor() as cur:
                    cur.execute(f'SET search_path = "{schema_name}", public;')
                    cur.execute(baseline_sql)
                duration = int((time.monotonic() - t_baseline) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=2,
                        type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                        status=ExperimentStepStatus.PASSED,
                        duration_ms=duration,
                    )
                )
            except Exception as exc:
                duration = int((time.monotonic() - t_baseline) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=2,
                        type=ExperimentStepType.LOAD_BASELINE_SCHEMA,
                        status=ExperimentStepStatus.FAILED,
                        duration_ms=duration,
                        sql_state=getattr(exc, "sqlstate", None),
                        error_type=type(exc).__name__,
                        message=redact_secrets(str(exc)),
                    )
                )
                self._skip_remaining(step_results, 3)
                return step_results

            # 3. LOAD_SEED_DATA
            seed_sql = fixture.read_seed_data(root)
            t_seed = time.monotonic()
            try:
                with conn.cursor() as cur:
                    cur.execute(f'SET search_path = "{schema_name}", public;')
                    cur.execute(seed_sql)
                duration = int((time.monotonic() - t_seed) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=3,
                        type=ExperimentStepType.LOAD_SEED_DATA,
                        status=ExperimentStepStatus.PASSED,
                        duration_ms=duration,
                    )
                )
            except Exception as exc:
                duration = int((time.monotonic() - t_seed) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=3,
                        type=ExperimentStepType.LOAD_SEED_DATA,
                        status=ExperimentStepStatus.FAILED,
                        duration_ms=duration,
                        sql_state=getattr(exc, "sqlstate", None),
                        error_type=type(exc).__name__,
                        message=redact_secrets(str(exc)),
                    )
                )
                self._skip_remaining(step_results, 4)
                return step_results

            # 4. APPLY_MIGRATION
            migration_sql = fixture.read_migration(root)
            t_migration = time.monotonic()
            migration_failed = False
            try:
                with conn.cursor() as cur:
                    cur.execute(f'SET search_path = "{schema_name}", public;')
                    cur.execute(migration_sql)
                duration = int((time.monotonic() - t_migration) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=4,
                        type=ExperimentStepType.APPLY_MIGRATION,
                        status=ExperimentStepStatus.PASSED,
                        duration_ms=duration,
                    )
                )
            except Exception as exc:
                migration_failed = True
                duration = int((time.monotonic() - t_migration) * 1000)
                step_results.append(
                    ExperimentStepResult(
                        order=4,
                        type=ExperimentStepType.APPLY_MIGRATION,
                        status=ExperimentStepStatus.FAILED,
                        duration_ms=duration,
                        sql_state=getattr(exc, "sqlstate", None),
                        error_type=type(exc).__name__,
                        message=redact_secrets(str(exc)),
                    )
                )

            # 5. RUN_READ_QUERY
            t_query = time.monotonic()
            if migration_failed:
                step_results.append(
                    ExperimentStepResult(
                        order=5,
                        type=ExperimentStepType.RUN_READ_QUERY,
                        status=ExperimentStepStatus.SKIPPED,
                        duration_ms=0,
                        message="Skipped: migration failed with error",
                    )
                )
            else:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f'SET search_path = "{schema_name}", public;')
                        cur.execute(fixture.verification_sql)
                        row = cur.fetchone()
                        val = row[0] if row is not None and len(row) > 0 else None

                    duration = int((time.monotonic() - t_query) * 1000)
                    step_results.append(
                        ExperimentStepResult(
                            order=5,
                            type=ExperimentStepType.RUN_READ_QUERY,
                            status=ExperimentStepStatus.PASSED,
                            duration_ms=duration,
                            scalar_value=str(val) if val is not None else None,
                        )
                    )
                except Exception as exc:
                    duration = int((time.monotonic() - t_query) * 1000)
                    step_results.append(
                        ExperimentStepResult(
                            order=5,
                            type=ExperimentStepType.RUN_READ_QUERY,
                            status=ExperimentStepStatus.FAILED,
                            duration_ms=duration,
                            sql_state=getattr(exc, "sqlstate", None),
                            error_type=type(exc).__name__,
                            message=redact_secrets(str(exc)),
                        )
                    )

            # 6. CAPTURE_RESULT
            step_results.append(
                ExperimentStepResult(
                    order=6,
                    type=ExperimentStepType.CAPTURE_RESULT,
                    status=ExperimentStepStatus.PASSED,
                    duration_ms=1,
                    message="Captured experiment observations and SQL states",
                )
            )

        finally:
            # Drop schema CASCADE guaranteed in finally
            if conn is not None:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
                except Exception as clean_exc:
                    logger.warning("Failed to drop schema %s: %s", schema_name, clean_exc)
                try:
                    conn.close()
                except Exception:
                    pass

        return step_results

    def _skip_remaining(self, step_results: list[ExperimentStepResult], from_order: int) -> None:
        type_map = {
            3: (ExperimentStepType.LOAD_SEED_DATA, "Load seed data"),
            4: (ExperimentStepType.APPLY_MIGRATION, "Apply migration"),
            5: (ExperimentStepType.RUN_READ_QUERY, "Run verification query"),
            6: (ExperimentStepType.CAPTURE_RESULT, "Capture result"),
        }
        for order in range(from_order, 7):
            stype, label = type_map[order]
            step_results.append(
                ExperimentStepResult(
                    order=order,
                    type=stype,
                    status=ExperimentStepStatus.SKIPPED,
                    duration_ms=0,
                    message=f"Skipped: {label}",
                )
            )
