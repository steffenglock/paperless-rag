"""
Webhook endpoint for automatic document indexing.
Highly tolerant production version.
"""

import logging
from typing import Annotated, Optional, Dict, Any

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services.index_service import index_single_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])
DbSession = Annotated[Session, Depends(get_session)]

class WebhookResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[int] = None

@router.post("/document", response_model=WebhookResponse)
async def document_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSession,
):
    # Rohen Inhalt auslesen
    raw_body = await request.body()
    body_text = ""
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = f"[Form-Data/Binary: {str(e)}]"

    logger.info("Webhook empfangen. Inhalt: %s", body_text)

    # Versuche, eine ID aus dem Text zu extrahieren (falls vorhanden)
    doc_id = None
    
    # Einfache Suche nach Zahlenwerten, falls es sich um Form-Data handelt
    if "document_id=" in body_text:
        try:
            doc_id = int(body_text.split("document_id=")[1].split("&")[0])
        except (ValueError, IndexFormatter):
            pass
            
    # Falls es JSON ist, versuche strukturiert zu parsen
    if doc_id is None:
        try:
            payload = await request.json()
            if payload:
                if "document_id" in payload:
                    doc_id = payload["document_id"]
                elif "id" in payload:
                    doc_id = payload["id"]
                elif "document" in payload and isinstance(payload["document"], dict):
                    doc_id = payload["document"].get("id")
        except Exception:
            pass

    # Fallunterscheidung: ID gefunden oder leeres Paket
    if doc_id is not None:
        try:
            doc_id = int(doc_id)
            logger.info("Gültige Dokumenten-ID %d gefunden. Indexierung gestartet.", doc_id)
            background_tasks.add_task(index_single_document, session, doc_id)
            return WebhookResponse(success=True, message="Indexing queued.", document_id=doc_id)
        except (ValueError, TypeError):
            pass

    # Wenn das Paket leer ist ({}), antworten wir trotzdem mit 200 OK, damit Paperless Ruhe gibt
    logger.info("Webhook enthielt keine Dokumenten-ID. Anfrage ignoriert.")
    return WebhookResponse(success=True, message="Webhook received but no action required (empty payload).")

@router.get("/health")
def webhook_health():
    return {"status": "ok", "endpoint": "/api/webhook/document"}
