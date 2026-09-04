from app.analyzers.api_dependency import ApiDependencyAnalyzer
from app.schemas.api_contract import ApiChange, ApiChangeType
from app.schemas.dependency import (
    ChangeFact,
    DependencyMatchKind,
    SourceDocument,
    SourceScope,
)


def test_api_dependency_analyzer_matches_brackets_and_dots():
    code = """import httpx

USER_ENDPOINT = "/users/{id}"

def get_user_email(user_id: int) -> str:
    response = httpx.get(f"/users/{user_id}").json()
    email_val = response["email"].lower()
    return email_val

def get_alt(user_id: int):
    response = fetch(user_id)
    return response['email']

def get_prop(user_id: int):
    response = fetch(user_id)
    return response.email
"""
    api_change = ApiChange(
        change_type=ApiChangeType.REMOVE_RESPONSE_FIELD,
        method="GET",
        path="/users/{id}",
        status_code=200,
        media_type="application/json",
        field_name="email",
        schema_name="User",
        json_pointer="#/components/schemas/User/properties/email",
        destructive=True,
    )
    change_fact = ChangeFact(
        id="api:GET:/users/{id}:200:application/json:response:email:REMOVE_RESPONSE_FIELD",
        domain="API",
        api_change=api_change,
    )

    doc = SourceDocument(
        path="client/user_client.py",
        content=code,
        scope=SourceScope.APPLICATION,
        sha="test_sha",
        changed_in_pull_request=False,
    )

    analyzer = ApiDependencyAnalyzer()
    evidences = analyzer.analyze([change_fact], [doc])

    assert len(evidences) == 3
    assert evidences[0].match_kind == DependencyMatchKind.DIRECT_RESPONSE_FIELD_REFERENCE
    assert evidences[0].target.field == "email"
    assert evidences[0].target.path == "/users/{id}"
    assert evidences[0].changed_in_pull_request is False
    assert "response[\"email\"]" in evidences[0].excerpt


def test_api_dependency_analyzer_no_match():
    code = """def get_user_name(user_id: int) -> str:
    response = fetch(user_id)
    return response["name"]
"""
    api_change = ApiChange(
        change_type=ApiChangeType.REMOVE_RESPONSE_FIELD,
        method="GET",
        path="/users/{id}",
        status_code=200,
        media_type="application/json",
        field_name="email",
        schema_name="User",
        json_pointer="#/components/schemas/User/properties/email",
        destructive=True,
    )
    change_fact = ChangeFact(
        id="api:GET:/users/{id}:200:application/json:response:email:REMOVE_RESPONSE_FIELD",
        domain="API",
        api_change=api_change,
    )
    doc = SourceDocument(
        path="client/user_client.py",
        content=code,
        scope=SourceScope.APPLICATION,
        sha="test_sha",
        changed_in_pull_request=False,
    )

    analyzer = ApiDependencyAnalyzer()
    evidences = analyzer.analyze([change_fact], [doc])
    assert len(evidences) == 0
