"""
Text chunking service.

Splits document text into overlapping chunks suitable for embedding.
Uses a simple character-based sliding window approach – no external
dependencies required.
"""

import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 3000      # characters per chunk
DEFAULT_CHUNK_OVERLAP = 400    # overlap between consecutive chunks
MIN_CHUNK_LENGTH = 50          # ignore chunks shorter than this


@dataclass
class TextChunk:
    """A single chunk of text with metadata."""
    chunk_id: str          # unique ID: "{doc_id}_chunk_{index}"
    document_id: int       # Paperless document ID
    document_title: str
    text: str              # chunk text content
    chunk_index: int       # position within the document
    total_chunks: int      # total number of chunks for this document


def _clean_text(text: str) -> str:
    """
    Basic text cleaning:
    - Collapse multiple blank lines into one
    - Strip leading/trailing whitespace
    """
    import re
    # Replace 3+ newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Replace multiple spaces with single space
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_document(
    document_id: int,
    title: str,
    content: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    """
    Split a document's content into overlapping text chunks.

    Returns an empty list if the content is too short to be useful.
    """
    if not content or not content.strip():
        logger.debug("Document %d has no content – skipping", document_id)
        return []

    cleaned = _clean_text(content)

    if len(cleaned) < MIN_CHUNK_LENGTH:
        logger.debug(
            "Document %d content too short (%d chars) – skipping",
            document_id,
            len(cleaned),
        )
        return []

    # Split into chunks with overlap
    chunks: list[str] = []
    start = 0

    while start < len(cleaned):
        end = start + chunk_size

        # Try to break at a paragraph or sentence boundary
        if end < len(cleaned):
            # Look for paragraph break
            para_break = cleaned.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break
            else:
                # Look for sentence end
                for punct in (". ", "! ", "? ", ".\n"):
                    sent_break = cleaned.rfind(punct, start, end)
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + 1
                        break

        chunk_text = cleaned[start:end].strip()
        if len(chunk_text) >= MIN_CHUNK_LENGTH:
            chunks.append(chunk_text)

        # Move forward with overlap
        start = end - chunk_overlap
        if start >= len(cleaned):
            break

    total = len(chunks)
    result: list[TextChunk] = []

    for i, chunk_text in enumerate(chunks):
        chunk_id = f"doc_{document_id}_chunk_{i}"
        result.append(
            TextChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                document_title=title,
                text=chunk_text,
                chunk_index=i,
                total_chunks=total,
            )
        )

    logger.debug(
        "Document %d '%s' → %d chunks", document_id, title[:40], total
    )
    return result


def compute_content_hash(content: str) -> str:
    """Compute MD5 hash of content to detect document changes."""
    return hashlib.md5(content.encode()).hexdigest()
