import logging
from typing import Any

import yaml

from app.schemas.api_contract import ApiChange, ApiChangeType
from app.schemas.dependency import ChangeFact

logger = logging.getLogger(__name__)

MAX_SPEC_SIZE_BYTES = 1024 * 1024  # 1 MB limit
MAX_REF_DEPTH = 10


class OpenApiParseError(ValueError):
    """Raised when an OpenAPI document is invalid, too large, or violates security constraints."""

    pass


class OpenApiParser:
    """Parses OpenAPI 3.x specifications and detects breaking contract changes."""

    def parse_document(self, content: str) -> dict[str, Any]:
        if len(content.encode("utf-8")) > MAX_SPEC_SIZE_BYTES:
            raise OpenApiParseError("OpenAPI document exceeds maximum allowed size of 1 MB")

        try:
            # YAML parser handles both JSON and YAML seamlessly
            doc = yaml.safe_load(content)
        except Exception as exc:
            raise OpenApiParseError(f"Failed to parse OpenAPI document: {exc}") from exc

        if not isinstance(doc, dict):
            raise OpenApiParseError("Malformed OpenAPI document: root must be a mapping/object")

        openapi_version = doc.get("openapi")
        if not openapi_version or not str(openapi_version).startswith("3."):
            raise OpenApiParseError(
                f"Unsupported specification version: {openapi_version!r}. "
                "Only OpenAPI 3.x is supported."
            )

        return doc

    def resolve_ref(
        self,
        ref: str,
        root: dict[str, Any],
        visited: set[str] | None = None,
        depth: int = 0,
    ) -> dict[str, Any]:
        if depth > MAX_REF_DEPTH:
            raise OpenApiParseError(f"Exceeded maximum $ref depth of {MAX_REF_DEPTH}")

        ref_str = str(ref).strip()
        if (
            ref_str.startswith("http://")
            or ref_str.startswith("https://")
            or ref_str.startswith("//")
        ):
            raise OpenApiParseError(f"Remote $ref is forbidden for security: {ref_str!r}")

        if not ref_str.startswith("#/"):
            raise OpenApiParseError(
                f"Only local document references starting with '#/' are supported: {ref_str!r}"
            )

        visited = visited or set()
        if ref_str in visited:
            raise OpenApiParseError(f"Cyclic $ref detected: {ref_str!r}")
        visited.add(ref_str)

        parts = ref_str[2:].split("/")
        curr: Any = root
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(curr, dict) or part not in curr:
                raise OpenApiParseError(f"Could not resolve $ref pointer: {ref_str!r}")
            curr = curr[part]

        if isinstance(curr, dict) and "$ref" in curr:
            return self.resolve_ref(curr["$ref"], root, visited, depth + 1)

        if not isinstance(curr, dict):
            return {}

        return curr

    def resolve_schema(
        self,
        schema: dict[str, Any],
        root: dict[str, Any],
        depth: int = 0,
    ) -> tuple[dict[str, Any], str | None]:
        """Resolves $ref in schema.
        
        Returns the resolved dictionary and the schema name if from components.
        """
        schema_name = None
        if "$ref" in schema:
            ref_str = schema["$ref"]
            if ref_str.startswith("#/components/schemas/"):
                schema_name = ref_str.split("/")[-1]
            resolved = self.resolve_ref(ref_str, root, depth=depth)
            return resolved, schema_name
        return schema, None

    def extract_response_schemas(
        self,
        doc: dict[str, Any],
    ) -> dict[tuple[str, str, int, str], tuple[dict[str, Any], str | None]]:
        """Extracts schemas for all endpoints.

        Key: (method, path, status_code, media_type)
        Value: (properties_dict, schema_name)
        """
        results: dict[tuple[str, str, int, str], tuple[dict[str, Any], str | None]] = {}
        paths = doc.get("paths", {})
        if not isinstance(paths, dict):
            return results

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                op = path_item.get(method)
                if not isinstance(op, dict):
                    continue

                responses = op.get("responses", {})
                if not isinstance(responses, dict):
                    continue

                for status_str, resp_obj in responses.items():
                    try:
                        status_code = int(status_str)
                    except ValueError:
                        continue  # skip 'default' for now

                    if not isinstance(resp_obj, dict):
                        continue

                    if "$ref" in resp_obj:
                        resp_obj = self.resolve_ref(resp_obj["$ref"], doc)

                    content = resp_obj.get("content", {})
                    if not isinstance(content, dict):
                        continue

                    for media_type, media_obj in content.items():
                        if not isinstance(media_obj, dict):
                            continue
                        schema = media_obj.get("schema")
                        if not isinstance(schema, dict):
                            continue

                        resolved_schema, schema_name = self.resolve_schema(schema, doc)
                        props = resolved_schema.get("properties", {})
                        if isinstance(props, dict):
                            key = (method.upper(), path, status_code, media_type)
                            results[key] = (props, schema_name)

        return results

    def compare(
        self,
        base_content: str,
        head_content: str,
        spec_file_path: str = "openapi.yaml",
    ) -> list[ApiChange]:
        """Compares base OpenAPI spec vs head OpenAPI spec to identify breaking changes."""
        base_doc = self.parse_document(base_content)
        head_doc = self.parse_document(head_content)

        base_schemas = self.extract_response_schemas(base_doc)
        head_schemas = self.extract_response_schemas(head_doc)

        changes: list[ApiChange] = []

        for key, (base_props, base_schema_name) in base_schemas.items():
            method, path, status_code, media_type = key
            if key not in head_schemas:
                continue

            head_props, _ = head_schemas[key]

            # Check for removed fields
            for field_name in base_props:
                if field_name not in head_props:
                    pointer = (
                        f"#/paths/{path.replace('/', '~1')}/{method.lower()}/"
                        f"responses/{status_code}/content/{media_type.replace('/', '~1')}/"
                        f"schema/properties/{field_name}"
                    )
                    changes.append(
                        ApiChange(
                            change_type=ApiChangeType.REMOVE_RESPONSE_FIELD,
                            method=method,
                            path=path,
                            status_code=status_code,
                            media_type=media_type,
                            field_name=field_name,
                            schema_name=base_schema_name,
                            json_pointer=pointer,
                            destructive=True,
                            spec_file_path=spec_file_path,
                        )
                    )

        return changes


def compute_api_change_id(change: ApiChange) -> str:
    """Computes a deterministic stable ID for an API ChangeFact."""
    return (
        f"api:{change.method}:{change.path}:{change.status_code}:"
        f"{change.media_type}:response:{change.field_name}:{change.change_type}"
    )


def build_api_change_facts(
    changes: list[ApiChange],
    spec_file_path: str,
    content_sha: str | None = None,
) -> list[ChangeFact]:
    facts: list[ChangeFact] = []
    for idx, ch in enumerate(changes):
        fact_id = compute_api_change_id(ch)
        facts.append(
            ChangeFact(
                id=fact_id,
                domain="API",
                sql_file_path="",
                content_sha=content_sha,
                statement_index=idx,
                change=None,
                api_change=ch,
            )
        )
    return facts
