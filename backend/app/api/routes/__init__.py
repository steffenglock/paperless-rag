"""
Central router registration for the FastAPI application.
All routers are imported here so that main.py can load them from a single package.
"""

from .config import router as config_router
from .paperless import router as paperless_router
from .index import router as index_router
from .rag import router as rag_router
from .sync import router as sync_router

# Damit die main.py die Router exakt unter diesen Namen importieren kann
__all__ = [
    "config_router",
    "paperless_router",
    "index_router",
    "rag_router",
    "sync_router",
]
