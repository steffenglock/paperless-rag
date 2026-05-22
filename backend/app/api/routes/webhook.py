"""
Webhook endpoint for automatic document indexing.
Diagnose-Version zum Sichtbarmachen der Paperless-Daten.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
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
    # 1. Den absolut rohen Inhalt der Anfrage auslesen
    raw_body = await request.body()
    # In Text umwandeln (Sollten Binärdaten kommen, fangen wir Fehler ab)
    body_text = ""
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = f"[Binärdaten/Nicht-UTF8: {str(e)} - Erste 100 Bytes: {str(raw_body[:100])}]"

    # 2. Exakte Ausgabe im Log erzwingen (Das ist unser Diagnose-Fenster!)
    logger.error("!!! DIAGNOSE - START !!!")
    logger.error("Roher Webhook-Inhalt von Paperless: %s", body_text)
    logger.error("Content-Type Header: %s", request.headers.get("content-type"))
    logger.error("!!! DIAGNOSE - ENDE !!!")

    # Wir brechen hier absichtlich kontrolliert ab, bis wir das Log analysiert haben
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Diagnose-Modus aktiv. Bitte Log prüfen.",
    )

@router.get("/health")
def webhook_health():
    return {"status": "ok", "endpoint": "/api/webhook/document"}
