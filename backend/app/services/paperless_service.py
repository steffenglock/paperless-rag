"""
Paperless-ngx API client service.

Provides methods to:
- Test the connection (GET /api/documents/)
- List all documents (GET /api/documents/)
- Fetch a single document with full content (GET /api/documents/{id}/)
- Iterate all documents page by page
"""

import logging
from typing import AsyncIterator, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.document import (
    ConnectionTestResult,
    PaperlessDocument,
    PaperlessDocumentList,
)

logger = logging.getLogger(__name__)

# Paperless-ngx returns max 25 results per page by default; we request more
PAGE_SIZE = 100
# Timeout for API requests in seconds
REQUEST_TIMEOUT = 30


def _make_client(base_url: str, token: str) -> httpx.AsyncClient:
    """Create an authenticated httpx client for the Paperless-ngx API."""
    return httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT,
    )


async def test_connection(base_url: str, token: str) -> ConnectionTestResult:
    """
    Test the connection to Paperless-ngx.
    Calls GET /api/documents/ to verify URL and token, then counts documents.
    """
    if not base_url or not token:
        return ConnectionTestResult(
            success=False,
            message="Paperless URL and token must not be empty.",
        )

    try:
        async with _make_client(base_url, token) as client:
            # Use documents endpoint directly – root /api/ redirects in newer versions
            response = await client.get(
                "/api/documents/",
                params={"page_size": 1},
            )
            response.raise_for_status()
            data = response.json()
            count = data.get("count", 0)

            # Try to read version from UI settings endpoint
            version: Optional[str] = None
            try:
                ui_response = await client.get("/api/ui_settings/")
                if ui_response.status_code == 200:
                    ui_data = ui_response.json()
                    version = ui_data.get("display_name", None)
            except Exception:
                pass  # version is optional

            logger.info(
                "Paperless-ngx connection OK – %d documents found", count
            )
            return ConnectionTestResult(
                success=True,
                message=f"Connection successful. {count} documents found.",
                document_count=count,
                paperless_version=version,
            )

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 403:
            msg = "Authentication failed – check your API token."
        elif status == 404:
            msg = "API endpoint not found – check your Paperless URL."
        elif status == 302:
            msg = "Paperless-ngx is redirecting – check your URL."
        else:
            msg = f"HTTP error {status} from Paperless-ngx."
        logger.warning("Paperless connection test failed: %s", msg)
        return ConnectionTestResult(success=False, message=msg)

    except httpx.ConnectError:
        msg = f"Cannot reach Paperless-ngx at {base_url} – check the URL."
        logger.warning("Paperless connection test failed: %s", msg)
        return ConnectionTestResult(success=False, message=msg)

    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        logger.exception("Paperless connection test failed unexpectedly")
        return ConnectionTestResult(success=False, message=msg)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _get_page(
    client: httpx.AsyncClient, page: int
) -> PaperlessDocumentList:
    """Fetch a single page of documents from Paperless-ngx."""
    response = await client.get(
        "/api/documents/",
        params={
            "page": page,
            "page_size": PAGE_SIZE,
            "ordering": "id",
        },
    )
    response.raise_for_status()
    return PaperlessDocumentList(**response.json())


async def get_all_documents(
    base_url: str, token: str
) -> AsyncIterator[PaperlessDocument]:
    """
    Async generator that yields every document from Paperless-ngx.
    Handles pagination automatically.
    """
    async with _make_client(base_url, token) as client:
        page = 1
        total_fetched = 0

        while True:
            doc_list = await _get_page(client, page)

            for doc in doc_list.results:
                yield doc
                total_fetched += 1

            logger.debug(
                "Fetched page %d – %d/%d documents",
                page,
                total_fetched,
                doc_list.count,
            )

            # No more pages
            if doc_list.next is None:
                break
            page += 1


async def get_document(
    base_url: str, token: str, document_id: int
) -> Optional[PaperlessDocument]:
    """
    Fetch a single document by ID.
    Returns None if the document does not exist (404).
    """
    try:
        async with _make_client(base_url, token) as client:
            response = await client.get(f"/api/documents/{document_id}/")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return PaperlessDocument(**response.json())
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Failed to fetch document %d: HTTP %d",
            document_id,
            exc.response.status_code,
        )
        raise


async def get_document_count(base_url: str, token: str) -> int:
    """Return the total number of documents in Paperless-ngx."""
    async with _make_client(base_url, token) as client:
        response = await client.get(
            "/api/documents/", params={"page_size": 1}
        )
        response.raise_for_status()
        return response.json().get("count", 0)