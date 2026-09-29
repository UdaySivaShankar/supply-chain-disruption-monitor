"""Basic authorization structure for consequential endpoints.

The guard is intentionally opt-in: when ``API_KEY`` is not configured the API
behaves exactly as before, which keeps local development and the demonstration
flow unchanged. Setting ``API_KEY`` in the environment switches every
state-changing endpoint to require a matching ``X-API-Key`` header.
"""

import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from utils.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: Optional[str] = Security(api_key_header)) -> None:
    expected = settings.api_key
    if not expected:
        # Authorization disabled: no API key configured for this deployment.
        return

    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )
