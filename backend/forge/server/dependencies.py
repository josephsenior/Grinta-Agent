"""FastAPI dependency helpers for validating session API keys."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, status
from fastapi.params import Depends as DependsParam
from fastapi.security import APIKeyHeader

_SESSION_API_KEY = os.getenv("SESSION_API_KEY")
_SESSION_API_KEY_HEADER = APIKeyHeader(name="X-Session-API-Key", auto_error=False)


def check_session_api_key(
    session_api_key: str | None = Depends(_SESSION_API_KEY_HEADER),
) -> None:
    """Check the session API key and throw an exception if incorrect.

    Having this as a dependency means it appears in OpenAPI Docs.
    """
    if session_api_key != _SESSION_API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


def get_dependencies() -> list[DependsParam]:
    """Get list of FastAPI dependencies for request validation.

    Returns API key check dependency if session API key is configured.

    Returns:
        List of Depends objects for dependency injection

    """
    result: list[DependsParam] = []
    if _SESSION_API_KEY:
        result.append(Depends(check_session_api_key))
    return result
