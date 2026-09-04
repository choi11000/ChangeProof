from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str


class LiveResponse(BaseModel):
    status: Literal["ok"]


class ReadinessChecker:
    def __init__(self, sandbox_database_url: str) -> None:
        self._url = sandbox_database_url.replace("postgresql+psycopg://", "postgresql://")

    def sandbox_ready(self) -> bool:
        try:
            with psycopg.connect(self._url, connect_timeout=2) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return cursor.fetchone() == (1,)
        except Exception:
            return False


def get_readiness_checker() -> ReadinessChecker:
    return ReadinessChecker(get_settings().sandbox_database_url)


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, environment=settings.app_env)


@router.get("/health/live", response_model=LiveResponse)
def liveness() -> LiveResponse:
    return LiveResponse(status="ok")


@router.get("/health/ready")
def readiness(
    checker: ReadinessChecker = Depends(get_readiness_checker),  # noqa: B008
):
    ready = checker.sandbox_ready()
    body = {
        "status": "ready" if ready else "not_ready",
        "sandbox": "ready" if ready else "unavailable",
    }
    if ready:
        return body
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body)
