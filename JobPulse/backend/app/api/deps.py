"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_session
from ..models import Device

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_api_key(
    settings: SettingsDep,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """No-op unless JOBPULSE_API_KEY is configured."""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")


def get_device(
    session: SessionDep,
    token: Annotated[str, Path(min_length=8, max_length=200)],
) -> Device:
    device = session.scalar(select(Device).where(Device.apns_token == token))
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not registered")
    return device


DeviceDep = Annotated[Device, Depends(get_device)]
