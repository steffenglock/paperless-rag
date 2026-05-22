"""
Indexing orchestration service.

Coordinates:
1. Fetch documents from Paperless-ngx
2. Chunk each document's content
3. Generate embeddings
4. Store in ChromaDB
5. Track indexing state in SQLite
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.indexing import IndexedDocument, IndexingStatus, IndexingResult
from app.services import paperless_service
from app.services import config_service
from app.services.chunking_service import chunk_document, compute_content_hash
from app.services.embedding_service import embed_texts
from app.services.chroma_service import add_chunks, delete_document_chunks

logger = logging.getLogger(__name__)

# Global indexing state (single-worker, no Redis needed)
_indexing_state: IndexingStatus = IndexingStatus(
    is_running=False,
    total_documents=0,
    processed_documents=0,
    failed_documents=0,
    message="Idle",
)


def get_indexing_status() -> IndexingStatus:
    """Return the current indexing status."""
    return _indexing_state


def _update_state(**kwargs) -> None:
    """Update fields in the global indexing state."""
    global _indexing_state
    for key, value in kwargs.items():
        setattr(_indexing_state, key, value)


def _get_indexed_doc(
    session: Session, paperless_id: int
) -> Optional[IndexedDocument]:
    """Look up an indexed document record by Paperless ID."""
    return session.exec(
        select(IndexedDocument).where(
            IndexedDocument.paperless_id == paperless_id
        )
    ).first()


def _save_indexed_doc(
    session: Session,
    paperless_id: int,
    title: str,
    chunk_count: int,
    content_hash: str,
) -> None:
    """Upsert an IndexedDocument tracking record."""
    existing = _get_indexed_doc(session, paperless_id)
    now = datetime.now(timezone.utc).isoformat()

    if existing:
        existing.title = title
        existing.chunk_count = chunk_count
        existing.content_hash = content_hash
        existing.indexed_at = now
        session.add(existing)
    else:
        session.add(
            IndexedDocument(
                paperless_id=paperless_id,
                title=title,
                chunk_count=chunk_count,
                content_hash=content_hash,
                indexed_at=now,
            )
        )
    session.commit()


async def run_full_index(session: Session) -> IndexingResult:
    """
    Index all documents from Paperless-ngx.

    - Skips documents whose content has not changed (same hash).
    - Re-indexes documents whose content changed.
    - Runs synchronously inside a FastAPI BackgroundTask.
    """
    global _indexing_state

    if _indexing_state.is_running:
        return IndexingResult(
            success=False,
            total_documents=0,
            indexed_documents=0,
            skipped_documents=0,
            failed_documents=0,
            message="Indexing is already running.",
        )

    # Load credentials
    paperless_url = config_service.get_value(session, "paperless_url") or ""
    paperless_token = config_service.get_value(session, "paperless_token") or ""
    embedding_provider = config_service.get_value(session, "embedding_provider") or ""
    embedding_base_url = config_service.get_value(session, "embedding_base_url") or ""
    embedding_api_key = config_service.get_value(session, "embedding_api_key") or ""
    embedding_model = config_service.get_value(session, "embedding_model") or ""

    if not paperless_url or not paperless_token:
        return IndexingResult(
            success=False,
            total_documents=0,
            indexed_documents=0,
            skipped_documents=0,
            failed_documents=0,
            message="Paperless-ngx is not configured.",
        )

    if not embedding_model:
        return IndexingResult(
            success=False,
            total_documents=0,
            indexed_documents=0,
            skipped_documents=0,
            failed_documents=0,
            message="Embedding model is not configured.",
        )

    # Initialise state
    doc_count = await paperless_service.get_document_count(
        paperless_url, paperless_token
    )
    _update_state(
        is_running=True,
        total_documents=doc_count,
        processed_documents=0,
        failed_documents=0,
        current_document=None,
        message="Indexing started …",
    )

    indexed = 0
    skipped = 0
    failed = 0

    try:
        async for doc in paperless_service.get_all_documents(
            paperless_url, paperless_token
        ):
            _update_state(current_document=doc.title)

            try:
                content = doc.content or ""
                content_hash = compute_content_hash(content)

                # Check if already indexed with same content
                existing = _get_indexed_doc(session, doc.id)
                if existing and existing.content_hash == content_hash:
                    skipped += 1
                    _update_state(
                        processed_documents=indexed + skipped + failed,
                        message=f"Skipped (unchanged): {doc.title[:50]}",
                    )
                    continue

                # Chunk the document
                chunks = chunk_document(doc.id, doc.title, content)
                if not chunks:
                    skipped += 1
                    _update_state(
                        processed_documents=indexed + skipped + failed,
                        message=f"Skipped (no content): {doc.title[:50]}",
                    )
                    continue

                # Generate embeddings
                texts = [chunk.text for chunk in chunks]
                embeddings = await embed_texts(
                    texts,
                    provider=embedding_provider,
                    base_url=embedding_base_url,
                    api_key=embedding_api_key,
                    model=embedding_model,
                )

                # Remove old chunks if re-indexing
                if existing:
                    delete_document_chunks(doc.id)

                # Store in ChromaDB
                add_chunks(chunks, embeddings)

                # Track in SQLite
                _save_indexed_doc(
                    session, doc.id, doc.title, len(chunks), content_hash
                )

                indexed += 1
                _update_state(
                    processed_documents=indexed + skipped + failed,
                    message=f"Indexed: {doc.title[:50]}",
                )
                logger.info("Indexed document %d '%s'", doc.id, doc.title)

            except Exception as exc:
                failed += 1
                _update_state(
                    processed_documents=indexed + skipped + failed,
                    message=f"Failed: {doc.title[:50]} – {exc}",
                )
                logger.error(
                    "Failed to index document %d '%s': %s",
                    doc.id, doc.title, exc,
                )

    finally:
        _update_state(
            is_running=False,
            current_document=None,
            message=(
                f"Done. Indexed: {indexed}, "
                f"Skipped: {skipped}, "
                f"Failed: {failed}"
            ),
        )

    return IndexingResult(
        success=True,
        total_documents=doc_count,
        indexed_documents=indexed,
        skipped_documents=skipped,
        failed_documents=failed,
        message=(
            f"Indexing complete. "
            f"Indexed: {indexed}, Skipped: {skipped}, Failed: {failed}"
        ),
    )


async def index_single_document(
    session: Session, document_id: int
) -> IndexingResult:
    """
    Index (or re-index) a single document by its Paperless ID.
    Used by the webhook endpoint in Step 6.
    """
    paperless_url = config_service.get_value(session, "paperless_url") or ""
    paperless_token = config_service.get_value(session, "paperless_token") or ""
    embedding_provider = config_service.get_value(session, "embedding_provider") or ""
    embedding_base_url = config_service.get_value(session, "embedding_base_url") or ""
    embedding_api_key = config_service.get_value(session, "embedding_api_key") or ""
    embedding_model = config_service.get_value(session, "embedding_model") or ""

    doc = await paperless_service.get_document(
        paperless_url, paperless_token, document_id
    )
    if doc is None:
        return IndexingResult(
            success=False,
            total_documents=1,
            indexed_documents=0,
            skipped_documents=0,
            failed_documents=1,
            message=f"Document {document_id} not found in Paperless-ngx.",
        )

    try:
        content = doc.content or ""
        chunks = chunk_document(doc.id, doc.title, content)

        if not chunks:
            return IndexingResult(
                success=False,
                total_documents=1,
                indexed_documents=0,
                skipped_documents=1,
                failed_documents=0,
                message=f"Document '{doc.title}' has no indexable content.",
            )

        texts = [chunk.text for chunk in chunks]
        embeddings = await embed_texts(
            texts,
            provider=embedding_provider,
            base_url=embedding_base_url,
            api_key=embedding_api_key,
            model=embedding_model,
        )

        # Remove old chunks before re-indexing
        delete_document_chunks(doc.id)
        add_chunks(chunks, embeddings)

        content_hash = compute_content_hash(content)
        _save_indexed_doc(
            session, doc.id, doc.title, len(chunks), content_hash
        )

        logger.info(
            "Single-document index complete: %d '%s' (%d chunks)",
            doc.id, doc.title, len(chunks),
        )
        return IndexingResult(
            success=True,
            total_documents=1,
            indexed_documents=1,
            skipped_documents=0,
            failed_documents=0,
            message=f"Document '{doc.title}' indexed with {len(chunks)} chunks.",
        )

    except Exception as exc:
        logger.exception("Failed to index document %d", document_id)
        return IndexingResult(
            success=False,
            total_documents=1,
            indexed_documents=0,
            skipped_documents=0,
            failed_documents=1,
            message=str(exc),
        )


def delete_document(session: Session, document_id: int) -> None:
    """
    Remove a document completely from the RAG index.
    Deletes the chunks from ChromaDB and the tracking record from SQLite.
    """
    try:
        # 1. Remove vectors from ChromaDB
        delete_document_chunks(document_id)

        # 2. Remove tracking record from SQLite
        existing = _get_indexed_doc(session, document_id)
        if existing:
            session.delete(existing)
            session.commit()
            logger.info("Deleted document %d from RAG index and tracking database.", document_id)
        else:
            logger.info("Document %d not found in tracking database during deletion.", document_id)

    except Exception as exc:
        logger.exception("Failed to delete document %d from index.", document_id)
        raise
