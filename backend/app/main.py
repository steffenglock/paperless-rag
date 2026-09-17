"""
FastAPI application entry point.
Routes are registered here; services are initialised on startup.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import models so SQLModel.metadata is populated before init_db()
import app.models
from app import __version__

# Routers
from app.api.routes import (
    config_router,
    index_router,
    paperless_router,
    rag_router,
    sync_router,
)
from app.config import settings
from app.database import get_session, init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


async def periodic_sync_task():
    """Läuft im Hintergrund und triggert den Pull-Sync alle 60 Minuten (Stündlich)."""
    logger.info(
        "Periodischer Synchronisations-Task initialisiert. Warte 30 Sekunden vor dem ersten Lauf..."
    )
    await asyncio.sleep(30)

    while True:
        try:
            logger.info("Starte automatischen periodischen Pull-Sync (Stündlich)...")
            session_generator = get_session()
            session = next(session_generator)

            from app.api.routes.sync import pull_missing_documents

            bg_tasks = BackgroundTasks()
            await pull_missing_documents(background_tasks=bg_tasks, session=session)
            logger.info("Periodischer Pull-Sync erfolgreich abgeschlossen/angestoßen.")

        except HTTPException as http_err:
            if http_err.status_code == 400:
                logger.warning(
                    "Periodischer Sync übersprungen: Paperless API-URL oder Token sind im UI noch nicht konfiguriert."
                )
            else:
                logger.error(
                    "HTTP-Fehler im periodischen Sync-Task: %s", http_err.detail
                )
        except Exception:
            logger.exception("Unerwarteter Fehler im periodischen Sync-Task")

        # 3600 Sekunden = 1 Stunde Pause bis zum nächsten Abgleich
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    logger.info("Starting Paperless RAG backend …")
    init_db()
    logger.info("Database initialised at data_dir=%s", settings.data_dir)

    sync_task = asyncio.create_task(periodic_sync_task())

    yield

    logger.info("Shutting down Paperless RAG backend …")
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        logger.info("Periodischer Sync-Task erfolgreich beendet.")


app = FastAPI(
    title="Paperless RAG",
    description="RAG-powered search for Paperless-ngx documents",
    version=__version__,
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
app.include_router(sync_router)


# ── Health check ─────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Returns 200 when the backend is ready."""
    return {"status": "ok", "version": __version__}
