"""
Config API routes.

GET  /api/config          → return all settings (sensitive fields masked)
POST /api/config          → save / update settings
GET  /api/config/keys     → return setting keys without values (for frontend hints)
POST /api/config/reset    → delete all stored settings
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

DbSession = Annotated[Session, Depends(get_session)]


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class ConfigRead(BaseModel):
    """Shape of the config returned to the frontend (sensitive fields masked)."""
    paperless_url: str = ""
    paperless_token: str = ""
    llm_provider: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_provider: str = ""
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    webhook_secret: str = ""


class ConfigWrite(BaseModel):
    """
    Payload accepted when saving configuration.
    All fields are optional so the frontend can do partial updates.
    """
    paperless_url: str | None = None
    paperless_token: str | None = None
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    webhook_secret: str | None = None


class ConfigSaveResponse(BaseModel):
    success: bool
    message: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=ConfigRead)
def read_config(session: DbSession):
    """Return all configuration values (sensitive fields masked)."""
    raw = config_service.get_all(session)
    masked = config_service.mask_sensitive(raw)
    return ConfigRead(**masked)


@router.post("", response_model=ConfigSaveResponse)
def save_config(payload: ConfigWrite, session: DbSession):
    """
    Persist configuration values.
    Only non-None fields are written; existing values for omitted fields
    are preserved.
    """
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No configuration values provided.",
        )
    try:
        config_service.set_many(session, data)
        logger.info("Configuration updated: keys=%s", list(data.keys()))
        return ConfigSaveResponse(success=True, message="Configuration saved.")
    except Exception as exc:
        logger.exception("Failed to save configuration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/keys")
def list_keys():
    """Return the list of valid configuration key names."""
    return {"keys": config_service.CONFIG_KEYS}


@router.post("/reset", response_model=ConfigSaveResponse)
def reset_config(session: DbSession):
    """Delete all stored configuration (useful during setup wizard reset)."""
    for key in config_service.CONFIG_KEYS:
        config_service.delete_value(session, key)
    logger.warning("Configuration reset – all keys deleted.")
    return ConfigSaveResponse(success=True, message="Configuration reset.")