import hashlib
import re

from app.schemas.dependency import (
    ChangeFact,
    DependencyEvidence,
    DependencyMatchKind,
    DependencyTarget,
    DependencyTargetType,
    SourceDocument,
)


class ApiDependencyAnalyzer:
    """Discovers consumer source code dependencies for removed OpenAPI response fields."""

    def analyze(
        self,
        change_facts: list[ChangeFact],
        documents: list[SourceDocument],
    ) -> list[DependencyEvidence]:
        evidences: list[DependencyEvidence] = []

        api_facts = [cf for cf in change_facts if cf.domain == "API" and cf.api_change]
        if not api_facts:
            return evidences

        for fact in api_facts:
            ch = fact.api_change
            if not ch or not ch.field_name:
                continue

            field = ch.field_name
            # Regex to match response["field"], response['field'], or .field
            dict_pattern = re.compile(
                rf'(\b(?:response|res|data|user|item|result|payload|body)\[["\']{re.escape(field)}["\']\]|'
                rf"\b(?:response|res|data|user|item|result)\.{re.escape(field)}\b)",
                re.IGNORECASE,
            )

            target = DependencyTarget(
                type=DependencyTargetType.API_FIELD,
                table="",
                path=ch.path,
                field=field,
                change_ids=[fact.id],
            )

            for doc in documents:
                lines = doc.content.splitlines()

                for line_idx, line in enumerate(lines, start=1):
                    match = dict_pattern.search(line)
                    if match:
                        excerpt = line.strip()
                        # Form stable evidence ID
                        evidence_id_input = (
                            f"{doc.path}:{line_idx}:{target.path}:{target.field}:{excerpt}"
                        )
                        hash_digest = hashlib.sha256(evidence_id_input.encode("utf-8")).hexdigest()
                        evidence_id = f"ev_api_{hash_digest[:12]}"

                        evidences.append(
                            DependencyEvidence(
                                id=evidence_id,
                                target=target,
                                path=doc.path,
                                line=line_idx,
                                match_kind=DependencyMatchKind.DIRECT_RESPONSE_FIELD_REFERENCE,
                                excerpt=excerpt[:240],
                                source_scope=doc.scope,
                                source_sha=doc.sha,
                                changed_in_pull_request=doc.changed_in_pull_request,
                            )
                        )

        return evidences
