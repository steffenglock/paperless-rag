"""
Sync endpoint for pulling missing documents from Paperless-ngx.
Conserves tokens by fetching only new document metadata.
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.services import paperless_service, config_service, chroma_service
from app.services.index_service import index_single_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])
DbSession = Annotated[Session, Depends(get_session)]

@router.post("/pull")
async def pull_missing_documents(
    background_tasks: BackgroundTasks,
    session: DbSession
):
    """
    Vergleicht alle Dokumenten-IDs aus Paperless-ngx mit ChromaDB
    und indexiert gezielt nur die fehlenden Dokumente im Hintergrund.
    """
    base_url = config_service.get_value(session, "paperless_url")
    token = config_service.get_value(session, "paperless_token")
    
    if not base_url or not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paperless API-URL oder Token nicht konfiguriert."
        )

    try:
        # 1. Alle IDs aus Paperless holen (Korrekt als Pydantic-Attribut doc.id ausgelesen)
        logger.info("Hole Dokumentenliste von Paperless-ngx...")
        paperless_ids = set()
        
        async for doc in paperless_service.get_all_documents(base_url, token):
            if doc and hasattr(doc, "id") and doc.id is not None:
                paperless_ids.add(int(doc.id))
        
        logger.info("Menge der IDs in Paperless gefunden: %d", len(paperless_ids))
        
        # 2. Bereits indexierte IDs aus ChromaDB ermitteln (Großes Limit setzen)
        collection = chroma_service.get_collection()
        existing_data = collection.get(include=["metadatas"], limit=10000)
        
        indexed_ids = set()
        if existing_data and "metadatas" in existing_data:
            for meta in existing_data["metadatas"]:
                if meta:
                    for key in ["document_id", "id", "doc_id"]:
                        if key in meta and meta[key] is not None:
                            try:
                                indexed_ids.add(int(meta[key]))
                            except (ValueError, TypeError):
                                continue

        logger.info("Menge der bereits indizierten Dokument-IDs in RAG: %d", len(indexed_ids))

        # 3. Differenz berechnen
        missing_ids = paperless_ids - indexed_ids
        
        if not missing_ids:
            logger.info("Pull-Sync beendet: Alles auf dem neuesten Stand.")
            return {
                "success": True,
                "message": "Alles aktuell. Keine neuen Dokumente zu indexieren.",
                "processed_count": 0
            }
            
        logger.info("Pull-Sync startet: %d neue Dokumente werden zur Indexierung queued. IDs: %s", len(missing_ids), list(missing_ids))
        
        # 4. Nur die fehlenden IDs in die Queue packen
        for doc_id in missing_ids:
            background_tasks.add_task(index_single_document, session, doc_id)
            
        return {
            "success": True,
            "message": f"Synchronisation gestartet. {len(missing_ids)} Dokumente werden im Hintergrund verarbeitet.",
            "processed_count": len(missing_ids),
            "document_ids": list(missing_ids)
        }

    except Exception as e:
        logger.error("Fehler beim Pull-Sync: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Synchronisation: {str(e)}"
        )
