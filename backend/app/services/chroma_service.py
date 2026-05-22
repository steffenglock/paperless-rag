"""
ChromaDB vector store service.

Uses ChromaDB in embedded mode – no separate server needed.
The database is stored in the data directory alongside SQLite.
"""

import logging
import os
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.chunking_service import TextChunk

logger = logging.getLogger(__name__)

# Collection name in ChromaDB
COLLECTION_NAME = "paperless_documents"


def _get_client() -> chromadb.Client:
    """Create or reuse a ChromaDB persistent client."""
    chroma_path = os.path.join(settings.data_dir, "chromadb")
    os.makedirs(chroma_path, exist_ok=True)
    return chromadb.PersistentClient(
        path=chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection() -> chromadb.Collection:
    """Get or create the documents collection."""
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # cosine similarity
    )


def add_chunks(
    chunks: list[TextChunk],
    embeddings: list[list[float]],
) -> None:
    """
    Add text chunks with their embeddings to ChromaDB.
    Existing chunks with the same ID are overwritten (upsert).
    """
    if not chunks:
        return

    collection = get_collection()

    ids = [chunk.chunk_id for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [
        {
            "document_id": chunk.document_id,
            "document_title": chunk.document_title,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
        }
        for chunk in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.debug("Upserted %d chunks into ChromaDB", len(chunks))


def delete_document_chunks(document_id: int) -> None:
    """Remove all chunks belonging to a specific document."""
    collection = get_collection()
    collection.delete(
        where={"document_id": document_id},
    )
    logger.debug("Deleted chunks for document %d from ChromaDB", document_id)


def query_collection(
    query_embedding: list[float],
    n_results: int = 5,
    document_ids: Optional[list[int]] = None,
) -> list[dict]:
    """
    Query ChromaDB for the most similar chunks.

    Returns a list of dicts with keys:
      id, text, document_id, document_title, chunk_index, distance
    """
    collection = get_collection()

    where = None
    if document_ids:
        where = {"document_id": {"$in": document_ids}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i, chunk_id in enumerate(results["ids"][0]):
        output.append(
            {
                "id": chunk_id,
                "text": results["documents"][0][i],
                "document_id": results["metadatas"][0][i]["document_id"],
                "document_title": results["metadatas"][0][i]["document_title"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "distance": results["distances"][0][i],
            }
        )

    return output


def get_collection_stats() -> dict:
    """Return basic statistics about the ChromaDB collection."""
    collection = get_collection()
    count = collection.count()
    return {
        "total_chunks": count,
        "collection_name": COLLECTION_NAME,
    }
