"""
SQLite database setup via SQLModel.
The database file is stored in the configured data directory.
"""

import os
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# Ensure data directory exists
os.makedirs(settings.data_dir, exist_ok=True)

DB_PATH = os.path.join(settings.data_dir, "paperless_rag.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=(settings.log_level == "DEBUG"),
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
)


def init_db() -> None:
    """Create all tables defined via SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency: yields a database session."""
    with Session(engine) as session:
        yield session
