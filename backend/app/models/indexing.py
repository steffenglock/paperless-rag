"""
SQLModel table and Pydantic models for indexing state tracking.
"""

from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import BaseModel


class IndexedDocument(SQLModel, table=True):
    """Tracks which documents have been indexed and when."""

    __tablename__ = "indexed_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    paperless_id: int = Field(index=True, unique=True)
    title: str = Field(default="")
    chunk_count: int = Field(default=0)
    indexed_at: str = Field(default="")   # ISO timestamp string
    content_hash: str = Field(default="") # MD5 of content to detect changes


class IndexingStatus(BaseModel):
    """Current indexing job status returned to the frontend."""
    is_running: bool
    total_documents: int
    processed_documents: int
    failed_documents: int
    current_document: Optional[str] = None
    message: str = ""


class IndexingResult(BaseModel):
    """Result returned after an indexing job completes."""
    success: bool
    total_documents: int
    indexed_documents: int
    skipped_documents: int
    failed_documents: int
    message: str
