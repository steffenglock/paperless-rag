"""
RAG (Retrieval-Augmented Generation) service.

Pipeline:
1. Embed the user query
2. Search ChromaDB for the most relevant chunks
3. Build a context string from the retrieved chunks
4. Send context + query to the LLM
5. Return the answer (with source references)
"""

import logging
import re
import unicodedata
from collections.abc import AsyncIterator

from sqlmodel import Session, select

from app.config import settings
from app.models.indexing import IndexedDocument
from app.services import config_service, llm_service
from app.services.chroma_service import query_collection
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)

# Ten retrieved chunks pair with the default 12,000-character complete-excerpt budget.
DEFAULT_RAG_N_RESULTS = 10
CONTEXT_BUDGET_MESSAGE = (
    "Relevant documents were found, but none fit within the configured context budget."
)


def _build_context(chunks: list[dict]) -> str:
    """
    Build a readable context string from retrieved chunks.
    Each chunk is prefixed with its source document title.
    """
    parts: list[str] = []
    seen_docs: set[int] = set()

    for i, chunk in enumerate(chunks, 1):
        doc_id = chunk["document_id"]
        title = chunk["document_title"]
        text = chunk["text"]

        seen_docs.add(doc_id)
        parts.append(f'[Excerpt {i} – from document: "{title}" (ID: {doc_id})]\n{text}')

    return "\n\n---\n\n".join(parts)


def _prepare_context(
    query: str,
    chunks: list[dict],
    max_context_chars: int,
) -> tuple[str, list[dict]]:
    """Select complete chunks that fit and build their shared LLM context."""
    selected: list[dict] = []
    context = ""

    normalized_query = _normalize_title(query)

    def priority(chunk: dict) -> tuple[bool, int]:
        normalized_title = _normalize_title(chunk["document_title"])
        title_match_length = (
            len(normalized_title)
            if _query_mentions_title(normalized_query, chunk["document_title"])
            else 0
        )
        return (
            not _query_mentions_document_id(normalized_query, chunk["document_id"]),
            -title_match_length,
        )

    prioritized_chunks = sorted(chunks, key=priority)

    for chunk in prioritized_chunks:
        candidate_chunks = [*selected, chunk]
        candidate_context = _build_context(candidate_chunks)
        if len(candidate_context) <= max_context_chars:
            selected = candidate_chunks
            context = candidate_context

    dropped_chunk_count = len(chunks) - len(selected)
    if dropped_chunk_count:
        logger.info(
            "RAG context budget excluded chunks",
            extra={
                "event": "rag_context_budget_exceeded",
                "retrieved_chunk_count": len(chunks),
                "selected_chunk_count": len(selected),
                "dropped_chunk_count": dropped_chunk_count,
                "context_budget_chars": max_context_chars,
            },
        )

    return context, selected


def _normalize_title(value: str) -> str:
    """Normalize Unicode, case and whitespace for exact title matching."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _query_mentions_title(normalized_query: str, title: str) -> bool:
    normalized_title = _normalize_title(title)
    if not normalized_title:
        return False
    return (
        re.search(rf"(?<!\w){re.escape(normalized_title)}(?!\w)", normalized_query)
        is not None
    )


def _query_mentions_document_id(normalized_query: str, document_id: int) -> bool:
    """Match IDs only after an explicit document/ID marker, never as substrings."""
    marker = r"(?:(?:document|dokument)(?:\s*-\s*|\s+)(?:id)?|id)"
    return (
        re.search(
            rf"(?<!\w){marker}[:#]?\s*(?<!\d){re.escape(str(document_id))}(?!\d)",
            normalized_query,
        )
        is not None
    )


def _retrieve_chunks(
    query: str,
    query_embedding: list[float],
    session: Session,
    n_results: int,
) -> list[dict]:
    """Retrieve explicit document matches before deduplicated semantic results."""
    normalized_query = _normalize_title(query)
    indexed_documents = session.exec(select(IndexedDocument)).all()
    explicit_documents = sorted(
        (
            document
            for document in indexed_documents
            if _query_mentions_document_id(normalized_query, document.paperless_id)
            or _query_mentions_title(normalized_query, document.title)
        ),
        key=lambda document: (
            not _query_mentions_document_id(normalized_query, document.paperless_id),
            -len(_normalize_title(document.title)),
        ),
    )
    explicit_document_ids = list(
        dict.fromkeys(document.paperless_id for document in explicit_documents)
    )

    chunks: list[dict] = []
    if explicit_document_ids:
        chunks.extend(
            query_collection(
                query_embedding,
                n_results=n_results,
                document_ids=explicit_document_ids,
            )
        )
    chunks.extend(query_collection(query_embedding, n_results=n_results))

    unique_chunks: list[dict] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        if chunk["id"] not in seen_chunk_ids:
            unique_chunks.append(chunk)
            seen_chunk_ids.add(chunk["id"])
    return unique_chunks


def _build_prompt(query: str, context: str) -> str:
    """Combine the retrieved context and user query into a single prompt."""
    return (
        f"The following excerpts are from documents in the document "
        f"management system:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Question: {query}\n\n"
        f"Please answer the question based on the excerpts above."
    )


def _get_llm_config(session: Session) -> dict:
    """Load LLM configuration from the database."""
    return {
        "provider": config_service.get_value(session, "llm_provider") or "",
        "base_url": config_service.get_value(session, "llm_base_url") or "",
        "api_key": config_service.get_value(session, "llm_api_key") or "",
        "model": config_service.get_value(session, "llm_model") or "",
    }


def _get_embedding_config(session: Session) -> dict:
    """Load embedding configuration from the database."""
    return {
        "provider": config_service.get_value(session, "embedding_provider") or "",
        "base_url": config_service.get_value(session, "embedding_base_url") or "",
        "api_key": config_service.get_value(session, "embedding_api_key") or "",
        "model": config_service.get_value(session, "embedding_model") or "",
    }


async def search_and_answer(
    query: str,
    session: Session,
    n_results: int = DEFAULT_RAG_N_RESULTS,
) -> dict:
    """
    Full RAG pipeline – returns answer + source chunks.
    """
    emb_config = _get_embedding_config(session)
    llm_config = _get_llm_config(session)

    if not llm_config["model"]:
        return {
            "answer": "LLM is not configured. Please complete the setup.",
            "sources": [],
            "query": query,
        }

    if not emb_config["model"]:
        return {
            "answer": "Embedding model is not configured. Please complete the setup.",
            "sources": [],
            "query": query,
        }

    # 1. Embed the query (Session wird mitgereicht)
    logger.info("Starting RAG query", extra={"event": "rag_query_started"})
    query_embedding = await embed_query(
        query,
        provider=emb_config["provider"],
        base_url=emb_config["base_url"],
        api_key=emb_config["api_key"],
        model=emb_config["model"],
        session=session,
    )

    # 2. Retrieve relevant chunks from ChromaDB
    chunks = _retrieve_chunks(query, query_embedding, session, n_results)

    if not chunks:
        return {
            "answer": "No relevant documents found for your query.",
            "sources": [],
            "query": query,
        }

    logger.info("Retrieved %d chunks from ChromaDB", len(chunks))

    # 3. Build context and prompt
    context, selected_chunks = _prepare_context(
        query, chunks, max_context_chars=settings.rag_context_max_chars
    )
    if not selected_chunks:
        return {
            "answer": CONTEXT_BUDGET_MESSAGE,
            "sources": [],
            "query": query,
        }

    prompt = _build_prompt(query, context)

    # 4. Get LLM answer
    answer = await llm_service.complete(
        prompt,
        provider=llm_config["provider"],
        base_url=llm_config["base_url"],
        api_key=llm_config["api_key"],
        model=llm_config["model"],
    )

    # 5. Return answer + sources
    sources = [
        {
            "document_id": chunk["document_id"],
            "document_title": chunk["document_title"],
            "text": chunk["text"][:300] + "…"
            if len(chunk["text"]) > 300
            else chunk["text"],
            "distance": round(chunk["distance"], 4),
        }
        for chunk in selected_chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "query": query,
    }


async def stream_answer(
    query: str,
    session: Session,
    n_results: int = DEFAULT_RAG_N_RESULTS,
) -> AsyncIterator[str]:
    """
    Streaming RAG pipeline – yields answer tokens as they arrive.
    """
    emb_config = _get_embedding_config(session)
    llm_config = _get_llm_config(session)

    # Embed query (Session wird mitgereicht)
    query_embedding = await embed_query(
        query,
        provider=emb_config["provider"],
        base_url=emb_config["base_url"],
        api_key=emb_config["api_key"],
        model=emb_config["model"],
        session=session,
    )

    chunks = _retrieve_chunks(query, query_embedding, session, n_results)

    if not chunks:
        yield "No relevant documents found for your query."
        return

    context, selected_chunks = _prepare_context(
        query, chunks, max_context_chars=settings.rag_context_max_chars
    )
    if not selected_chunks:
        yield CONTEXT_BUDGET_MESSAGE
        return

    prompt = _build_prompt(query, context)

    async for token in llm_service.stream_complete(
        prompt,
        provider=llm_config["provider"],
        base_url=llm_config["base_url"],
        api_key=llm_config["api_key"],
        model=llm_config["model"],
    ):
        yield token
