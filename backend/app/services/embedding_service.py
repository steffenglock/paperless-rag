"""
Embedding service.

Supports:
- Ollama  (local, via OpenAI-compatible API)
- OpenAI  (api.openai.com)
- OpenRouter (openrouter.ai)

All three use the same openai Python client with different base_url values.
"""

import logging
from typing import Optional
from sqlmodel import Session
from openai import AsyncOpenAI

from app.config import settings
from app.services import config_service

logger = logging.getLogger(__name__)

# Batch size for embedding requests (avoid overloading the API)
EMBEDDING_BATCH_SIZE = 32


def _make_embedding_client(
    provider: str,
    base_url: str,
    api_key: str,
) -> AsyncOpenAI:
    """
    Create an AsyncOpenAI client configured for the given provider.
    Ollama uses http://host:11434/v1 and accepts any non-empty api_key.
    """
    # Verhindere leere Keys, die den "Bearer "-Header beschädigen
    final_key = api_key if (api_key and api_key.strip() != "") else "not-empty"

    if provider == "ollama":
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/v1" if base_url else "http://localhost:11434/v1",
            api_key=final_key,
        )
    else:
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=final_key,
        )


async def embed_texts(
    texts: list[str],
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    session: Optional[Session] = None,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Falls back to DB config if a session is provided, otherwise to settings.
    """
    # 1. Prio: Explizit übergebene Parameter
    # 2. Prio: Werte aus der DB (falls Session vorhanden)
    # 3. Prio: Globale Umgebungsvariablen (Settings)
    if session:
        _provider = provider or config_service.get_value(session, "embedding_provider") or settings.embedding_provider
        _base_url = base_url or config_service.get_value(session, "embedding_base_url") or settings.embedding_base_url
        _api_key = api_key or config_service.get_value(session, "embedding_api_key") or settings.embedding_api_key
        _model = model or config_service.get_value(session, "embedding_model") or settings.embedding_model
    else:
        _provider = provider or settings.embedding_provider
        _base_url = base_url or settings.embedding_base_url
        _api_key = api_key or settings.embedding_api_key
        _model = model or settings.embedding_model

    client = _make_embedding_client(_provider, _base_url, _api_key)

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        logger.debug(
            "Embedding batch %d-%d with model '%s'",
            i,
            i + len(batch),
            _model,
        )
        response = await client.embeddings.create(
            model=_model,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_query(
    query: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    session: Optional[Session] = None,
) -> list[float]:
    """Embed a single query string. Returns one float vector."""
    results = await embed_texts(
        [query],
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        session=session,
    )
    return results[0]
