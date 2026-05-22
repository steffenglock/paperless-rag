"""
Webhook endpoint for automatic document indexing.

Paperless-ngx can call this endpoint when a document is added or updated.
The endpoint triggers re-indexing of the affected document.

Paperless-ngx webhook configuration:
  URL:    http://<paperless-rag-host>:3000/api/webhook/document
  Method: POST
  Events: document_added, document_updated
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_webhook_secret(
    secret: str,
    payload_body: str,
    signature_header: Optional[str],
) -> bool:
    """
    Verify HMAC-SHA256 signature if a webhook secret is configured.
    Returns True if no secret is configured (open endpoint).
    """
    if not secret:
        return True   # no secret configured – allow all requests

    if not signature_header:
        logger.warning("Webhook request missing signature header")
        return False

    expected = hmac.new(
        secret.encode(),
        payload_body.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/document", response_model=WebhookResponse)
async def document_webhook(
    request: Request,  # Nutzen des rohen Request-Objekts für maximale Flexibilität beim JSON-Format
    background_tasks: BackgroundTasks,
    session: DbSession,
    x_webhook_secret: Annotated[Optional[str], Header()] = None,
):
    """
    Receives a webhook call from Paperless-ngx and triggers
    re-indexing of the affected document in the background.
    Supports both old flat JSON payloads and new nested workflow formats.
    """
    # Rohes JSON einlesen, um Schema-Fehler (422) bei verschachtelten Strukturen zu verhindern
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error("Invalid JSON received in webhook: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        )

    logger.debug("Webhook payload received: %s", payload)

    doc_id = None

    # Flexibles Extrahieren der Dokumenten-ID aus verschiedenen Paperless-Formaten
    # 1. Flache Struktur (Standard Webhooks oder ältere Versionen)
    if "id" in payload and payload["id"] is not None:
        doc_id = payload["id"]
    elif "document_id" in payload and payload["document_id"] is not None:
        doc_id = payload["document_id"]
    # 2. Verschachtelte Struktur (Paperless-ngx ab v2.0+ via Workflows)
    elif "document" in payload and isinstance(payload["document"], dict):
        doc_id = payload["document"].get("id")
    elif "data" in payload and isinstance(payload["data"], dict):
        doc_id = payload["data"].get("id")

    if doc_id is None:
        logger.error("No valid document ID found in webhook payload. Fields present: %s", list(payload.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain a valid document ID.",
        )

    # Typ-Sicherheit garantieren (ID muss eine Ganzzahl sein)
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
            logger.warning(
                "Webhook request with invalid secret for document %d", doc_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret.",
            )

    logger.info(
        "Webhook received: event=%s document_id=%d",
        payload.get("event") or "unknown",
        doc_id,
    )

    # Index the document in the background
    background_tasks.add_task(index_single_document, session, doc_id)

    return WebhookResponse(
        success=True,
        message=f"Document {doc_id} queued for indexing.",
        document_id=doc_id,
    )


@router.get("/health")
def webhook_health():
    """Simple health check for the webhook endpoint."""
    return {"status": "ok", "endpoint": "/api/webhook/document"}