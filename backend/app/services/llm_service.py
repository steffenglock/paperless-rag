"""
LLM service.

Supports Ollama, OpenAI and OpenRouter via the openai Python client.
Provides both standard and streaming completion methods.
"""

import logging
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# System prompt for RAG responses
RAG_SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent der Fragen zu Dokumenten aus einem Paperless-ngx Dokumenten-Management-System beantwortet.

WICHTIGE REGELN:
- Beantworte die Frage AUSSCHLIESSLICH auf Basis der bereitgestellten Dokumentenauszüge.
- Antworte IMMER in der gleichen Sprache wie die Frage. Wenn die Frage auf Deutsch ist, antworte auf Deutsch. Wenn die Frage auf Englisch ist, antworte auf Englisch.
- Wenn die Antwort nicht in den Auszügen gefunden werden kann, sage das klar.
- Nenne immer welche(s) Dokument(e) deine Antwort belegt.
- Sei präzise und konkret.

You are a helpful assistant. ALWAYS answer in the same language as the user's question. If the question is in German, answer in German. If the question is in English, answer in English."""


def _make_llm_client(
    provider: str,
    base_url: str,
    api_key: str,
) -> AsyncOpenAI:
    """Create an AsyncOpenAI client for the given LLM provider."""
    if provider == "ollama":
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/v1",
            api_key=api_key or "ollama",
        )
    else:
        return AsyncOpenAI(
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=api_key,
        )


async def complete(
    prompt: str,
    system_prompt: str = RAG_SYSTEM_PROMPT,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Send a prompt to the LLM and return the complete response as a string.
    """
    _provider = provider or settings.llm_provider
    _base_url = base_url or settings.llm_base_url
    _api_key = api_key or settings.llm_api_key
    _model = model or settings.llm_model

    client = _make_llm_client(_provider, _base_url, _api_key)

    logger.debug("LLM request: provider=%s model=%s", _provider, _model)

    response = await client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content or ""
    logger.debug("LLM response: %d chars", len(content))
    return content


async def stream_complete(
    prompt: str,
    system_prompt: str = RAG_SYSTEM_PROMPT,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream a response from the LLM token by token.
    Yields text chunks as they arrive.
    """
    _provider = provider or settings.llm_provider
    _base_url = base_url or settings.llm_base_url
    _api_key = api_key or settings.llm_api_key
    _model = model or settings.llm_model

    client = _make_llm_client(_provider, _base_url, _api_key)

    logger.debug(
        "LLM stream request: provider=%s model=%s", _provider, _model
    )

    stream = await client.chat.completions.create(
        model=_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
