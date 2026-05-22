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
from typing import AsyncIterator, Optional

from app.services.embedding_service import embed_query
from app.services.chroma_service import query_collection
from app.services import llm_service, config_service
from sqlmodel import Session

logger = logging.getLogger(__name__)

# How many chunks to retrieve from ChromaDB
DEFAULT_N_RESULTS = 5
# Maximum characters of context to send to the LLM
MAX_CONTEXT_CHARS = 6000


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
        parts.append(
            f"[Excerpt {i} – from document: \"{title}\" (ID: {doc_id})]\n"
            f"{text}"
        )

    return "\n\n---\n\n".join(parts)


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
    n_results: int = DEFAULT_N_RESULTS,
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
    logger.info("RAG query: '%s'", query[:80])
    query_embedding = await embed_query(
        query,
        provider=emb_config["provider"],
        base_url=emb_config["base_url"],
        api_key=emb_config["api_key"],
        model=emb_config["model"],
        session=session,
    )

    # 2. Retrieve relevant chunks from ChromaDB
    chunks = query_collection(query_embedding, n_results=n_results)

    if not chunks:
        return {
            "answer": "No relevant documents found for your query.",
            "sources": [],
            "query": query,
        }

    logger.info("Retrieved %d chunks from ChromaDB", len(chunks))

    # 3. Build context and prompt
    context = _build_context(chunks)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated…]"

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
            "text": chunk["text"][:300] + "…" if len(chunk["text"]) > 300 else chunk["text"],
            "distance": round(chunk["distance"], 4),
        }
        for chunk in chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "query": query,
    }


async def stream_answer(
    query: str,
    session: Session,
    n_results: int = DEFAULT_N_RESULTS,
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

    chunks = query_collection(query_embedding, n_results=n_results)

    if not chunks:
        yield "No relevant documents found for your query."
        return

    context = _build_context(chunks)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated…]"

    prompt = _build_prompt(query, context)

    async for token in llm_service.stream_complete(
        prompt,
        provider=llm_config["provider"],
        base_url=llm_config["base_url"],
        api_key=llm_config["api_key"],
        model=llm_config["model"],
    ):
        yield token
