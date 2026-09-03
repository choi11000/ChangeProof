import re
from collections.abc import Iterable

from app.core.redaction import redact_lines
from app.schemas.dependency import (
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


def extract_dependency_targets(sql_files: list[SqlFileAnalysis]) -> list[DependencyTarget]:
    """Extract distinct schema targets from analyzed SQL migration changes."""
    targets: list[DependencyTarget] = []
    seen: set[tuple[DependencyTargetType, str, str | None]] = set()

    for file_analysis in sql_files:
        if not file_analysis.analysis:
            continue
        for change in file_analysis.analysis.changes:
            if change.operation in COLUMN_OPERATIONS and change.table and change.column:
                key = (DependencyTargetType.COLUMN, change.table.lower(), change.column.lower())
                if key not in seen:
                    seen.add(key)
                    targets.append(
                        DependencyTarget(
                            type=DependencyTargetType.COLUMN,
                            table=change.table,
                            column=change.column,
                            source_change=change,
                        )
                    )
            elif change.operation in TABLE_OPERATIONS and change.table:
                key = (DependencyTargetType.TABLE, change.table.lower(), None)
                if key not in seen:
                    seen.add(key)
                    targets.append(
                        DependencyTarget(
                            type=DependencyTargetType.TABLE,
                            table=change.table,
                            column=None,
                            source_change=change,
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

        col_regexes = [
            re.compile(r"\b" + re.escape(var) + r"\b", re.IGNORECASE) for var in column_variants
        ]
        table_regexes = [
            re.compile(r"\b" + re.escape(var) + r"\b", re.IGNORECASE) for var in table_variants
        ]

        # Qualified patterns:
        # 1. Attribute access on any object or table: obj.column or Order.column or self.column
        attr_pattern = re.compile(
            r"(?:\b[A-Za-z_][A-Za-z0-9_]*\s*\.\s*(?:"
            + "|".join(re.escape(var) for var in column_variants)
            + r")\b)",
            re.IGNORECASE,
        )
        # 2. Dictionary/bracket access: obj["column"] or obj['column']
        dict_pattern = re.compile(
            r"""(?:\[\s*['"](?:\s*"""
            + "|".join(re.escape(var) for var in column_variants)
            + r""")['"]\s*\])""",
            re.IGNORECASE,
        )

        matches: list[DependencyEvidence] = []

        for line_index, line in enumerate(lines):
            line_num = line_index + 1
            has_col_match = any(regex.search(line) for regex in col_regexes)
            if not has_col_match:
                continue

            # Check for qualified reference first
            is_attr_ref = bool(attr_pattern.search(line))
            is_dict_ref = bool(dict_pattern.search(line))

            match_kind: DependencyMatchKind
            if is_attr_ref or is_dict_ref:
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
            matches.append(
                DependencyEvidence(
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
            matches.append(
                DependencyEvidence(
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
