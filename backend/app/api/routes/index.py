"""
Indexing API routes.

POST /api/index/start         → start full indexing (background task)
GET  /api/index/status        → current indexing status
GET  /api/index/stats         → ChromaDB + SQLite stats
POST /api/index/document/{id} → index a single document
DELETE /api/index/document/{id} → remove a document from the index
"""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.indexing import IndexedDocument, IndexingResult, IndexingStatus
from app.services import index_service
from app.services.chroma_service import (
    delete_document_chunks,
    get_collection_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/index", tags=["indexing"])

DbSession = Annotated[Session, Depends(get_session)]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=IndexingResult)
async def start_indexing(
    background_tasks: BackgroundTasks,
    session: DbSession,
):
    """
    Start a full indexing run in the background.
    Returns immediately; poll /api/index/status for progress.
    """
    if index_service.get_indexing_status().is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Indexing is already running.",
        )

    # Run indexing as a background task
    background_tasks.add_task(index_service.run_full_index, session)

    return IndexingResult(
        success=True,
        total_documents=0,
        indexed_documents=0,
        skipped_documents=0,
        failed_documents=0,
        message="Indexing started in the background. "
                "Poll /api/index/status for progress.",
    )


@router.get("/status", response_model=IndexingStatus)
def get_status():
    """Return the current indexing job status."""
    return index_service.get_indexing_status()


@router.get("/stats")
def get_stats(session: DbSession):
    """Return indexing statistics from SQLite and ChromaDB."""
    chroma_stats = get_collection_stats()

    # Count indexed documents in SQLite
    indexed_docs = session.exec(select(IndexedDocument)).all()

    return {
        "indexed_document_count": len(indexed_docs),
        "total_chunks": chroma_stats["total_chunks"],
        "collection_name": chroma_stats["collection_name"],
        "documents": [
            {
                "paperless_id": doc.paperless_id,
                "title": doc.title,
                "chunk_count": doc.chunk_count,
                "indexed_at": doc.indexed_at,
            }
            for doc in indexed_docs[:20]   # return first 20 for preview
        ],
    }


@router.post("/document/{document_id}", response_model=IndexingResult)
async def index_single_document(document_id: int, session: DbSession):
    """Index or re-index a single document by its Paperless-ngx ID."""
    return await index_service.index_single_document(session, document_id)


@router.delete("/document/{document_id}")
def remove_document(document_id: int, session: DbSession):
    """Remove a document and all its chunks from the index."""
    # Remove from ChromaDB
    delete_document_chunks(document_id)

    # Remove from SQLite tracking table
    existing = session.exec(
        select(IndexedDocument).where(
            IndexedDocument.paperless_id == document_id
        )
    ).first()

    if existing:
        session.delete(existing)
        session.commit()

    return {"success": True, "message": f"Document {document_id} removed from index."}
