"""
Paperless-ngx API routes.

POST /api/paperless/test-connection   → test URL + token from DB
GET  /api/paperless/documents         → list documents (paginated)
GET  /api/paperless/documents/{id}    → fetch single document
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models.document import ConnectionTestResult, PaperlessDocument
from app.services import config_service
from app.services import paperless_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paperless", tags=["paperless"])

DbSession = Annotated[Session, Depends(get_session)]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_paperless_credentials(session: Session) -> tuple[str, str]:
    """
    Load Paperless URL and token from the database.
    Raises 400 if not configured.
    """
    url = config_service.get_value(session, "paperless_url") or ""
    token = config_service.get_value(session, "paperless_token") or ""
    if not url or not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paperless URL and token are not configured. "
                   "Please complete the setup first.",
        )
    return url, token


# ── Schemas ───────────────────────────────────────────────────────────────────

class TestConnectionPayload(BaseModel):
    """
    Optional payload for connection test.
    If provided, these values are used instead of the stored ones.
    Useful during the setup wizard before saving.
    """
    paperless_url: Optional[str] = None
    paperless_token: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""
    count: int
    page: int
    page_size: int
    results: list[PaperlessDocument]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    payload: TestConnectionPayload,
    session: DbSession,
):
    """
    Test the Paperless-ngx connection.
    Uses provided credentials if given and not masked,
    otherwise loads from DB.
    """
    # Use payload values only if they are provided AND not masked (no • character)
    use_payload_url = payload.paperless_url and "•" not in payload.paperless_url
    use_payload_token = payload.paperless_token and "•" not in payload.paperless_token

    if use_payload_url and use_payload_token:
        url = payload.paperless_url
        token = payload.paperless_token
    else:
        # Always load fresh unmasked values from DB
        url, token = _get_paperless_credentials(session)

    return await paperless_service.test_connection(url, token)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    """
    Return a paginated list of documents from Paperless-ngx.
    Documents are fetched live from the Paperless API.
    """
    url, token = _get_paperless_credentials(session)

    # Collect documents for the requested page
    all_docs: list[PaperlessDocument] = []
    async for doc in paperless_service.get_all_documents(url, token):
        all_docs.append(doc)

    # Manual pagination over the full list
    total = len(all_docs)
    start = (page - 1) * page_size
    end = start + page_size

    return DocumentListResponse(
        count=total,
        page=page,
        page_size=page_size,
        results=all_docs[start:end],
    )


@router.get("/documents/{document_id}", response_model=PaperlessDocument)
async def get_document(document_id: int, session: DbSession):
    """Fetch a single document by its Paperless-ngx ID."""
    url, token = _get_paperless_credentials(session)

    doc = await paperless_service.get_document(url, token, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found in Paperless-ngx.",
        )
    return doc


@router.get("/status")
async def paperless_status(session: DbSession):
    """
    Return connection status and document count.
    Used by the frontend status bar.
    """
    url = config_service.get_value(session, "paperless_url") or ""
    token = config_service.get_value(session, "paperless_token") or ""

    if not url or not token:
        return {
            "configured": False,
            "connected": False,
            "document_count": 0,
            "message": "Not configured",
        }

    result = await paperless_service.test_connection(url, token)
    return {
        "configured": True,
        "connected": result.success,
        "document_count": result.document_count or 0,
        "message": result.message,
    }