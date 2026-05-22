"""
Webhook endpoint for automatic document indexing.

Paperless-ngx can call this endpoint when a document is added or updated.
The endpoint triggers re-indexing of the affected document.
"""

import hashlib
import hmac
import logging
from typing import Annotated, Optional, Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks, Request, status
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services import config_service
from app.services.index_service import index_single_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

DbSession = Annotated[Session, Depends(get_session)]


# ── Schemas ───────────────────────────────────────────────────────────────────

class WebhookResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[int] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/document", response_model=WebhookResponse)
async def document_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSession,
    x_webhook_secret: Annotated[Optional[str], Header()] = None,
):
    """
    Receives a webhook call from Paperless-ngx and triggers
    re-indexing of the affected document in the background.
    Supports JSON payloads, multi-part form data, and fallback form parameters.
    """
    payload: Dict[str, Any] = {}
    
    # 1. Versuch: Extrahiere Formulardaten (Falls Paperless Parameter schickt)
    try:
        form_data = await request.form()
        if form_data:
            payload = dict(form_data)
            logger.debug("Webhook Form-Data empfangen: %s", payload)
    except Exception:
        pass

    # 2. Versuch: Falls Form-Data leer war, versuche JSON auszulesen
    if not payload:
        try:
            payload = await request.json()
            logger.debug("Webhook JSON empfangen: %s", payload)
        except Exception:
            pass

    doc_id = None

    # Flexibles Auslesen der ID aus allen denkbaren Paperless-Varianten
    if "document_id" in payload and payload["document_id"] is not None:
        doc_id = payload["document_id"]
    elif "id" in payload and payload["id"] is not None:
        doc_id = payload["id"]
    elif "document" in payload and isinstance(payload["document"], dict):
        doc_id = payload["document"].get("id")
    elif "data" in payload and isinstance(payload["data"], dict):
        doc_id = payload["data"].get("id")

    # Absicherung: Falls Paperless die Parameter als Rohdaten/Strings geschickt hat
    if doc_id is None and payload:
        # Falls ein Key existiert, der die ID enthält (z.B. bei Falschformatierungen)
        for key, value in payload.items():
            if "id" in key.lower():
                doc_id = value
                break

    if doc_id is None:
        logger.error("Keine ID im Payload gefunden. Empfangene Daten: %s", payload)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain a valid document ID.",
        )

    # Typ-Sicherheit garantieren (ID zu Integer konvertieren)
    try:
        doc_id = int(doc_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document ID must be an integer.",
        )

    # Check webhook secret if configured
    webhook_secret = config_service.get_value(session, "webhook_secret") or ""
    if webhook_secret:
        if not x_webhook_secret or x_webhook_secret != webhook_secret:
            logger.warning("Webhook request mit ungültigem Secret für Dokument %d", doc_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret.",
            )

    logger.info("Webhook erfolgreich empfangen und akzeptiert! Dokumenten-ID=%d", doc_id)

    # Index the document in the background
    background_tasks.add_task(index_single_document, session, doc_id)

    return WebhookResponse(
        success=True,
        message=f"Document {doc_id} queued for indexing.",
        document_id=doc_id,
    )


@router.get("/health")
def webhook_health():
    return {"status": "ok", "endpoint": "/api/webhook/document"}