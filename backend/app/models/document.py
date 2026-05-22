"""
Pydantic models for Paperless-ngx document data.
These are NOT database tables – they represent API response shapes.
"""

from typing import Optional
from pydantic import BaseModel


class PaperlessDocument(BaseModel):
    """Represents a single document from the Paperless-ngx API."""
    id: int
    title: str
    content: str = ""          # plain text extracted by Paperless
    created: Optional[str] = None
    modified: Optional[str] = None
    correspondent: Optional[int] = None
    document_type: Optional[int] = None
    tags: list[int] = []
    original_file_name: Optional[str] = None


class PaperlessDocumentList(BaseModel):
    """Paginated list response from Paperless-ngx."""
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[PaperlessDocument] = []


class ConnectionTestResult(BaseModel):
    """Result of a Paperless-ngx connection test."""
    success: bool
    message: str
    document_count: Optional[int] = None
    paperless_version: Optional[str] = None
