import pytest

from app.analyzers.openapi_parser import OpenApiParseError, OpenApiParser, build_api_change_facts
from app.schemas.api_contract import ApiChangeType

BASE_SPEC_YAML = """
openapi: "3.0.0"
info:
  title: Sample API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      summary: Get user
      responses:
        "200":
          description: User found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
        name:
          type: string
"""

HEAD_SPEC_YAML_FIELD_REMOVED = """
openapi: "3.0.0"
info:
  title: Sample API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      summary: Get user
      responses:
        "200":
          description: User found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
"""

HEAD_SPEC_YAML_ADDITIVE = """
openapi: "3.0.0"
info:
  title: Sample API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      summary: Get user
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
        name:
          type: string
        role:
          type: string
"""


def test_openapi_parser_detects_removed_field():
    parser = OpenApiParser()
    changes = parser.compare(
        base_content=BASE_SPEC_YAML,
        head_content=HEAD_SPEC_YAML_FIELD_REMOVED,
        spec_file_path="openapi.yaml",
    )
    assert len(changes) == 1
    change = changes[0]
    assert change.change_type == ApiChangeType.REMOVE_RESPONSE_FIELD
    assert change.method == "GET"
    assert change.path == "/users/{id}"
    assert change.status_code == 200
    assert change.media_type == "application/json"
    assert change.field_name == "email"
    assert change.schema_name == "User"
    assert "email" in change.json_pointer

    facts = build_api_change_facts(changes, "openapi.yaml")
    assert len(facts) == 1
    assert facts[0].domain == "API"
    assert facts[0].id.startswith("api:GET:/users/{id}:200:application/json:response:email:")


def test_openapi_parser_additive_field_no_breaking_change():
    parser = OpenApiParser()
    changes = parser.compare(
        base_content=BASE_SPEC_YAML,
        head_content=HEAD_SPEC_YAML_ADDITIVE,
        spec_file_path="openapi.yaml",
    )
    assert len(changes) == 0


def test_openapi_parser_inline_schema():
    base_inline = """
openapi: "3.0.0"
info:
  title: Inline API
  version: "1.0.0"
paths:
  /items:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  sku:
                    type: string
                  price:
                    type: number
"""
    head_inline = """
openapi: "3.0.0"
info:
  title: Inline API
  version: "1.0.0"
paths:
  /items:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  sku:
                    type: string
"""
    parser = OpenApiParser()
    changes = parser.compare(base_inline, head_inline, "openapi.json")
    assert len(changes) == 1
    assert changes[0].field_name == "price"
    assert changes[0].path == "/items"


def test_openapi_parser_remote_ref_refused():
    spec_with_remote = """
openapi: "3.0.0"
info:
  title: Remote API
  version: "1.0.0"
paths:
  /external:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "https://example.com/schema.json"
"""
    parser = OpenApiParser()
    with pytest.raises(OpenApiParseError, match="Remote \\$ref is forbidden"):
        parser.compare(spec_with_remote, spec_with_remote, "openapi.yaml")


def test_openapi_parser_cyclic_ref_safe():
    cyclic_spec = """
openapi: "3.0.0"
info:
  title: Cyclic API
  version: "1.0.0"
paths:
  /nodes:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/NodeA"
components:
  schemas:
    NodeA:
      $ref: "#/components/schemas/NodeB"
    NodeB:
      $ref: "#/components/schemas/NodeA"
"""
    parser = OpenApiParser()
    with pytest.raises(OpenApiParseError, match="Cyclic \\$ref detected"):
        parser.compare(cyclic_spec, cyclic_spec, "openapi.yaml")


def test_openapi_parser_malformed_spec():
    parser = OpenApiParser()
    with pytest.raises(OpenApiParseError):
        parser.parse_document("::: this is not valid yaml or json")


def test_openapi_parser_size_limit():
    parser = OpenApiParser()
    huge_spec = "openapi: 3.0.0\n" + "x: " + "y" * (1024 * 1024 + 50)
    with pytest.raises(OpenApiParseError, match="exceeds maximum allowed size"):
        parser.parse_document(huge_spec)


def test_openapi_parser_multiple_removed_fields():
    base_multi = """
openapi: "3.0.0"
info:
  title: API
  version: "1.0.0"
paths:
  /users:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  a: {type: string}
                  b: {type: string}
                  c: {type: string}
"""
    head_multi = """
openapi: "3.0.0"
info:
  title: API
  version: "1.0.0"
paths:
  /users:
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  c: {type: string}
"""
    parser = OpenApiParser()
    changes = parser.compare(base_multi, head_multi, "openapi.yaml")
    removed_fields = {c.field_name for c in changes}
    assert removed_fields == {"a", "b"}
