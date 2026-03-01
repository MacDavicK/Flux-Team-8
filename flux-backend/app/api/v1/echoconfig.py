"""
/_echoconfig — Basic-Auth-protected endpoint that dumps the resolved config.

Credentials: one / piece
"""
from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

router = APIRouter(tags=["internal"])

_security = HTTPBasic()

_USERNAME = "one"
_PASSWORD = "piece"


def _require_basic_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    ok_user = secrets.compare_digest(credentials.username.encode(), _USERNAME.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), _PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/_echoconfig")
def echoconfig(_: None = Depends(_require_basic_auth)) -> dict:
    """
    Returns the full resolved config.

    - Pydantic settings (sourced from .env / env vars) are always shown.
    - In non-development environments every os.environ entry is also included
      so variables injected at the platform level (e.g. Railway, Render, Fly)
      are visible alongside the declared settings.
    """
    declared = settings.model_dump()

    env_vars: dict[str, str] | None = None
    if settings.app_env != "development":
        env_vars = dict(os.environ)

    return {
        "app_env": settings.app_env,
        "settings": declared,
        **({"os_environ": env_vars} if env_vars is not None else {}),
    }
