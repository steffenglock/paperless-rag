"""
FastAPI application entry point.
Routes are registered here; services are initialised on startup.
"""

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, get_session

# Import models so SQLModel.metadata is populated before init_db()
import app.models  # noqa: F401

# Routers
from app.api.routes import (
    config_router,
    paperless_router,
    index_router,
    rag_router,
    webhook_router,
    sync_router, # Der über __init__.py registrierte Sync-Router
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


async def periodic_sync_task():
    """Läuft im Hintergrund und triggert den Pull-Sync alle 15 Minuten."""
    logger.info("Periodischer Synchronisations-Task initialisiert. Warte 30 Sekunden vor dem ersten Lauf...")
    await asyncio.sleep(30)  # Kurze Pause nach dem Booten, damit alle Dienste bereit sind
    
    while True:
        try:
            logger.info("Starte automatischen periodischen Pull-Sync...")
            # Wir holen uns eine Datenbanksitzung über den Generator
            session_generator = get_session()
            session = next(session_generator)
            
            # Wir rufen die Sync-Funktion direkt auf
            from app.api.routes.sync import pull_missing_documents
            bg_tasks = BackgroundTasks()
            await pull_missing_documents(background_tasks=bg_tasks, session=session)
            logger.info("Periodischer Pull-Sync erfolgreich angestoßen.")
        except Exception as e:
            logger.error("Fehler im periodischen Sync-Task: %s", str(e), exc_info=True)
            
        # 900 Sekunden = 15 Minuten Pause bis zum nächsten Abgleich
        await asyncio.sleep(900)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    logger.info("Starting Paperless RAG backend …")
    init_db()
    logger.info("Database initialised at data_dir=%s", settings.data_dir)
    
    # Startet den periodischen Sync-Timer als echten Hintergrundprozess
    sync_task = asyncio.create_task(periodic_sync_task())
    
    yield
    
    logger.info("Shutting down Paperless RAG backend …")
    # Beendet den Hintergrund-Task sauber, wenn der Container stoppt
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        logger.info("Periodischer Sync-Task erfolgreich beendet.")


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
app.include_router(sync_router)  # Registrierung unseres neuen Sync-Endpunkts


# ── Health check ─────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Returns 200 when the backend is ready."""
    return {"status": "ok", "version": "0.1.0"}
