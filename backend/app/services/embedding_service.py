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

from openai import AsyncOpenAI

from app.config import settings

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
    if provider == "ollama":
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/v1",
            api_key=api_key or "ollama",   # Ollama ignores the key
        )
    else:
        # OpenAI and OpenRouter both use the standard client
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=api_key,
        )


async def embed_texts(
    texts: list[str],
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Falls back to settings values if parameters are not provided.
    Returns a list of float vectors, one per input text.
    """
    _provider = provider or settings.embedding_provider
    _base_url = base_url or settings.embedding_base_url
    _api_key = api_key or settings.embedding_api_key
    _model = model or settings.embedding_model

    client = _make_embedding_client(_provider, _base_url, _api_key)

    all_embeddings: list[list[float]] = []

    # Process in batches
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
) -> list[float]:
    """Embed a single query string. Returns one float vector."""
    results = await embed_texts(
        [query],
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    return results[0]
