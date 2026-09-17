"""
Application configuration loaded from environment variables.
All sensitive values are read at startup; defaults are safe for local dev.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_RAG_CONTEXT_MAX_CHARS = 12000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paperless-ngx
    paperless_url: str = Field(default="http://localhost:8000")
    paperless_token: str = Field(default="")

    # LLM
    llm_provider: str = Field(default="ollama")
    llm_base_url: str = Field(default="http://localhost:11434")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="llama3.2")

    # Embeddings
    embedding_provider: str = Field(default="ollama")
    embedding_base_url: str = Field(default="http://localhost:11434")
    embedding_api_key: str = Field(default="")
    embedding_model: str = Field(default="nomic-embed-text")

    # Security
    encryption_key: str = Field(default="")

    # App
    log_level: str = Field(default="INFO")
    data_dir: str = Field(default="/app/data")
    # Complete excerpts only; sized for the API's default retrieval of 10 chunks.
    rag_context_max_chars: int = Field(
        default=DEFAULT_RAG_CONTEXT_MAX_CHARS,
        ge=1,
    )


# Singleton – import this everywhere
settings = Settings()
