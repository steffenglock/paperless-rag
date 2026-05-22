"""
CRUD service for application configuration.

All values are encrypted at rest using the encryption service.
The service exposes typed helpers for the most common settings,
plus generic get/set methods for arbitrary keys.
"""

from typing import Optional

from sqlmodel import Session, select

from app.models.config import ConfigEntry
from app.services.encryption import encrypt, decrypt


# ── Generic helpers ──────────────────────────────────────────────────────────

def get_value(session: Session, key: str) -> Optional[str]:
    """Return the decrypted value for *key*, or None if not found."""
    entry = session.exec(select(ConfigEntry).where(ConfigEntry.key == key)).first()
    if entry is None:
        return None
    return decrypt(entry.value_encrypted)


def set_value(session: Session, key: str, value: str) -> None:
    """Upsert *key* → encrypted *value* in the database."""
    entry = session.exec(select(ConfigEntry).where(ConfigEntry.key == key)).first()
    if entry is None:
        entry = ConfigEntry(key=key, value_encrypted=encrypt(value))
        session.add(entry)
    else:
        entry.value_encrypted = encrypt(value)
        session.add(entry)
    session.commit()


def delete_value(session: Session, key: str) -> bool:
    """Delete *key* from the database. Returns True if it existed."""
    entry = session.exec(select(ConfigEntry).where(ConfigEntry.key == key)).first()
    if entry is None:
        return False
    session.delete(entry)
    session.commit()
    return True


# ── Bulk helpers ─────────────────────────────────────────────────────────────

# All keys that the application manages
CONFIG_KEYS = [
    "paperless_url",
    "paperless_token",
    "llm_provider",
    "llm_base_url",
    "llm_api_key",
    "llm_model",
    "embedding_provider",
    "embedding_base_url",
    "embedding_api_key",
    "embedding_model",
    "webhook_secret",
]


def get_all(session: Session) -> dict[str, str]:
    """
    Return all known configuration keys as a plain dict.
    Missing keys are returned as empty strings.
    """
    result: dict[str, str] = {}
    for key in CONFIG_KEYS:
        value = get_value(session, key) or ""
        result[key] = value
    return result


def set_many(session: Session, data: dict[str, str]) -> None:
    """Persist multiple key-value pairs in a single transaction."""
    for key, value in data.items():
        if key in CONFIG_KEYS:
            set_value(session, key, value)


def mask_sensitive(data: dict[str, str]) -> dict[str, str]:
    """
    Return a copy of *data* with sensitive fields partially masked.
    Used before sending config back to the frontend.
    """
    sensitive = {"paperless_token", "llm_api_key", "embedding_api_key", "webhook_secret"}
    masked = dict(data)
    for field in sensitive:
        raw = masked.get(field, "")
        if raw:
            masked[field] = raw[:4] + "•" * max(0, len(raw) - 4)
    return masked