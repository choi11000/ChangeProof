from enum import StrEnum

from pydantic import BaseModel


class ApiChangeType(StrEnum):
    REMOVE_RESPONSE_FIELD = "REMOVE_RESPONSE_FIELD"
    ADD_RESPONSE_FIELD = "ADD_RESPONSE_FIELD"
    CHANGE_RESPONSE_FIELD_TYPE = "CHANGE_RESPONSE_FIELD_TYPE"


class ApiChange(BaseModel):
    change_type: ApiChangeType
    method: str
    path: str
    status_code: int = 200
    media_type: str = "application/json"
    field_name: str
    schema_name: str | None = None
    json_pointer: str = ""
    destructive: bool = True
    spec_file_path: str = ""


class ApiObservationCode(StrEnum):
    API_MISSING_RESPONSE_FIELD = "API_MISSING_RESPONSE_FIELD"
    API_UNEXPECTED_STATUS = "API_UNEXPECTED_STATUS"
    API_MALFORMED_RESPONSE = "API_MALFORMED_RESPONSE"
    API_PROBE_PASSED = "API_PROBE_PASSED"


class ApiObservation(BaseModel):
    domain: str = "API"
    status_code: int
    observation_code: ApiObservationCode
    json_pointer: str | None = None
    expected_field: str | None = None
    actual_payload: dict | list | str | int | float | bool | None = None
    message: str | None = None
