import hashlib
import re
from collections.abc import Iterable

from app.core.redaction import redact_lines
from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    ImpactSummary,
    SourceDocument,
    SourceScope,
)
from app.schemas.github import SqlFileAnalysis
from app.schemas.sql_change import SqlOperation

COLUMN_OPERATIONS = {
    SqlOperation.DROP_COLUMN,
    SqlOperation.ALTER_COLUMN_TYPE,
    SqlOperation.SET_NOT_NULL,
    SqlOperation.DROP_NOT_NULL,
    SqlOperation.SET_DEFAULT,
    SqlOperation.DROP_DEFAULT,
}

TABLE_OPERATIONS = {
    SqlOperation.DROP_TABLE,
}


def compute_change_id(
    sql_file_path: str,
    content_sha: str | None,
    statement_index: int,
    operation: str,
    table: str | None,
    column: str | None,
) -> str:
    """Generate a stable, deterministic identifier for a SQL change fact."""
    raw = (
        f"{sql_file_path}:{content_sha or ''}:{statement_index}:{operation}:"
        f"{table or ''}:{column or ''}"
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"change_{digest}"


def compute_evidence_id(
    target_type: str,
    target_table: str,
    target_column: str | None,
    path: str,
    line: int,
    match_kind: str,
) -> str:
    """Generate a stable, deterministic identifier for a dependency evidence match."""
    col_str = target_column.lower() if target_column else ""
    raw = f"{target_type}:{target_table.lower()}:{col_str}:{path}:{line}:{match_kind}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"ev_{digest}"


def build_change_facts(sql_files: list[SqlFileAnalysis]) -> list[ChangeFact]:
    """Build change facts with stable deterministic IDs from parsed SQL files."""
    facts: list[ChangeFact] = []
    for file_analysis in sql_files:
        if not file_analysis.analysis:
            continue
        for change in file_analysis.analysis.changes:
            cid = compute_change_id(
                file_analysis.path,
                file_analysis.content_sha,
                change.statement_index,
                change.operation.value,
                change.table,
                change.column,
            )
            facts.append(
                ChangeFact(
                    id=cid,
                    sql_file_path=file_analysis.path,
                    content_sha=file_analysis.content_sha,
                    statement_index=change.statement_index,
                    change=change,
                )
            )
    return facts


def extract_dependency_targets(
    sql_files: list[SqlFileAnalysis],
    change_facts: list[ChangeFact] | None = None,
) -> list[DependencyTarget]:
    """Extract schema targets, preserving change_ids for all changes touching the entity."""
    if change_facts is None:
        change_facts = build_change_facts(sql_files)

    targets_map: dict[tuple[DependencyTargetType, str, str | None], list[str]] = {}

    for fact in change_facts:
        if fact.domain == "API" and fact.api_change:
            ch = fact.api_change
            key = (DependencyTargetType.API_FIELD, ch.path, ch.field_name)
            targets_map.setdefault(key, []).append(fact.id)
            continue

        change = fact.change
        if not change:
            continue
        if change.operation in COLUMN_OPERATIONS and change.table and change.column:
            key = (DependencyTargetType.COLUMN, change.table, change.column)
            targets_map.setdefault(key, []).append(fact.id)
        elif change.operation in TABLE_OPERATIONS and change.table:
            key = (DependencyTargetType.TABLE, change.table, None)
            targets_map.setdefault(key, []).append(fact.id)

    targets: list[DependencyTarget] = []
    for (target_type, entity_or_path, col_or_field), cids in targets_map.items():
        if target_type == DependencyTargetType.API_FIELD:
            targets.append(
                DependencyTarget(
                    type=target_type,
                    table="",
                    path=entity_or_path,
                    field=col_or_field,
                    change_ids=cids,
                )
            )
        else:
            targets.append(
                DependencyTarget(
                    type=target_type,
                    table=entity_or_path,
                    column=col_or_field,
                    change_ids=cids,
                )
            )
    return targets


def _to_camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0].lower() + "".join(part.capitalize() for part in parts[1:])


def _to_pascal_case(value: str) -> str:
    parts = value.split("_")
    return "".join(part.capitalize() for part in parts)


def _singularize(name: str) -> str | None:
    lower = name.lower()
    if lower.endswith("ies") and len(lower) > 3:
        return lower[:-3] + "y"
    if lower.endswith("es") and len(lower) > 3:
        return lower[:-2]
    if lower.endswith("s") and len(lower) > 1 and not lower.endswith("ss"):
        return lower[:-1]
    return None


def get_column_variants(column: str) -> list[str]:
    variants: list[str] = [column]
    camel = _to_camel_case(column)
    pascal = _to_pascal_case(column)
    for variant in (camel, pascal):
        if variant not in variants:
            variants.append(variant)
    return variants


def get_table_variants(table: str) -> list[str]:
    variants: list[str] = [table]
    singular = _singularize(table)
    if singular and singular not in variants:
        variants.append(singular)

    base_list = list(variants)
    for name in base_list:
        camel = _to_camel_case(name)
        pascal = _to_pascal_case(name)
        for variant in (camel, pascal):
            if variant not in variants:
                variants.append(variant)
    return variants


class DependencyAnalyzer:
    """Pure deterministic analyzer discovering source code references to DB schema targets."""

    def analyze(
        self,
        targets: list[DependencyTarget],
        documents: list[SourceDocument],
    ) -> list[DependencyEvidence]:
        evidences: list[DependencyEvidence] = []
        for document in documents:
            evidences.extend(self._analyze_document(targets, document))
        return evidences

    def _analyze_document(
        self,
        targets: list[DependencyTarget],
        document: SourceDocument,
    ) -> list[DependencyEvidence]:
        lines = document.content.splitlines()
        evidences: list[DependencyEvidence] = []

        for target in targets:
            if target.type is DependencyTargetType.COLUMN:
                evidences.extend(self._match_column_target(target, document, lines))
            elif target.type is DependencyTargetType.TABLE:
                evidences.extend(self._match_table_target(target, document, lines))

        return evidences

    def _match_column_target(
        self,
        target: DependencyTarget,
        document: SourceDocument,
        lines: list[str],
    ) -> list[DependencyEvidence]:
        assert target.column is not None
        column_variants = get_column_variants(target.column)
        table_variants = get_table_variants(target.table)
        table_variant_lowers = {v.lower() for v in table_variants}

        col_regexes = [
            re.compile(r"\b" + re.escape(var) + r"\b", re.IGNORECASE) for var in column_variants
        ]
        table_regexes = [
            re.compile(r"\b" + re.escape(var) + r"\b", re.IGNORECASE) for var in table_variants
        ]

        # Attribute access: capture (qualifier).(column_variant)
        attr_regex = re.compile(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*("
            + "|".join(re.escape(var) for var in column_variants)
            + r")\b",
            re.IGNORECASE,
        )

        # Dictionary access: capture (qualifier)["column_variant"] or ['column_variant']
        dict_regex = re.compile(
            r"""\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*['"]\s*("""
            + "|".join(re.escape(var) for var in column_variants)
            + r""")\s*['"]\s*\]""",
            re.IGNORECASE,
        )

        matches: list[DependencyEvidence] = []

        for line_index, line in enumerate(lines):
            line_num = line_index + 1
            has_col_match = any(regex.search(line) for regex in col_regexes)
            if not has_col_match:
                continue

            # Hardening A: Check if qualifier specifically matches table variants
            has_table_qualified_ref = False
            for m in attr_regex.finditer(line):
                qualifier = m.group(1).lower()
                if qualifier in table_variant_lowers:
                    has_table_qualified_ref = True
                    break

            if not has_table_qualified_ref:
                for m in dict_regex.finditer(line):
                    qualifier = m.group(1).lower()
                    if qualifier in table_variant_lowers:
                        has_table_qualified_ref = True
                        break

            match_kind: DependencyMatchKind
            if has_table_qualified_ref:
                match_kind = DependencyMatchKind.QUALIFIED_REFERENCE
            else:
                # Check for table in vicinity (+-2 lines window)
                window_start = max(0, line_index - 2)
                window_end = min(len(lines), line_index + 3)
                context_window = lines[window_start:window_end]
                has_table_in_context = any(
                    any(t_regex.search(ctx_line) for t_regex in table_regexes)
                    for ctx_line in context_window
                )
                if has_table_in_context:
                    match_kind = DependencyMatchKind.TABLE_AND_COLUMN_CONTEXT
                else:
                    match_kind = DependencyMatchKind.COLUMN_IDENTIFIER

            excerpt = redact_lines(line.strip())
            ev_id = compute_evidence_id(
                target.type.value,
                target.table,
                target.column,
                document.path,
                line_num,
                match_kind.value,
            )
            matches.append(
                DependencyEvidence(
                    id=ev_id,
                    target=target,
                    path=document.path,
                    line=line_num,
                    match_kind=match_kind,
                    excerpt=excerpt,
                    source_scope=document.scope,
                    source_sha=document.sha,
                    changed_in_pull_request=document.changed_in_pull_request,
                )
            )

        return matches

    def _match_table_target(
        self,
        target: DependencyTarget,
        document: SourceDocument,
        lines: list[str],
    ) -> list[DependencyEvidence]:
        table_variants = get_table_variants(target.table)
        table_regexes = [
            re.compile(r"\b" + re.escape(var) + r"\b", re.IGNORECASE) for var in table_variants
        ]

        matches: list[DependencyEvidence] = []

        for line_index, line in enumerate(lines):
            line_num = line_index + 1
            has_table = any(regex.search(line) for regex in table_regexes)
            if not has_table:
                continue

            excerpt = redact_lines(line.strip())
            ev_id = compute_evidence_id(
                target.type.value,
                target.table,
                None,
                document.path,
                line_num,
                DependencyMatchKind.TABLE_IDENTIFIER.value,
            )
            matches.append(
                DependencyEvidence(
                    id=ev_id,
                    target=target,
                    path=document.path,
                    line=line_num,
                    match_kind=DependencyMatchKind.TABLE_IDENTIFIER,
                    excerpt=excerpt,
                    source_scope=document.scope,
                    source_sha=document.sha,
                    changed_in_pull_request=document.changed_in_pull_request,
                )
            )

        return matches


def summarize_impact(
    targets: Iterable[DependencyTarget],
    evidences: Iterable[DependencyEvidence],
    *,
    scan_complete: bool = True,
) -> ImpactSummary:
    target_list = list(targets)
    evidence_list = list(evidences)

    app_files = {
        ev.path for ev in evidence_list if ev.source_scope is SourceScope.APPLICATION
    }
    test_files = {
        ev.path for ev in evidence_list if ev.source_scope is SourceScope.TEST
    }

    qualified = sum(
        1 for ev in evidence_list if ev.match_kind is DependencyMatchKind.QUALIFIED_REFERENCE
    )
    contextual = sum(
        1 for ev in evidence_list if ev.match_kind is DependencyMatchKind.TABLE_AND_COLUMN_CONTEXT
    )
    identifier = sum(
        1
        for ev in evidence_list
        if ev.match_kind
        in (DependencyMatchKind.COLUMN_IDENTIFIER, DependencyMatchKind.TABLE_IDENTIFIER)
    )

    return ImpactSummary(
        targets=len(target_list),
        application_files_with_references=len(app_files),
        test_files_with_references=len(test_files),
        qualified_references=qualified,
        contextual_references=contextual,
        identifier_references=identifier,
        scan_complete=scan_complete,
    )
