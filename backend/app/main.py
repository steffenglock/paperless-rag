"""
FastAPI application entry point.
Routes are registered here; services are initialised on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

# Import models so SQLModel.metadata is populated before init_db()
import app.models  # noqa: F401

# Routers
from app.api.routes import (
    config_router,
    paperless_router,
    index_router,
    rag_router,
    webhook_router,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    logger.info("Starting Paperless RAG backend …")
    init_db()
    logger.info("Database initialised at data_dir=%s", settings.data_dir)
    yield
    logger.info("Shutting down Paperless RAG backend …")


app = FastAPI(
    title="Paperless RAG",
    description="RAG-powered search for Paperless-ngx documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(config_router)
app.include_router(paperless_router)
app.include_router(index_router)
app.include_router(rag_router)
app.include_router(webhook_router)


# ── Health check ─────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Returns 200 when the backend is ready."""
    return {"status": "ok", "version": "0.1.0"}