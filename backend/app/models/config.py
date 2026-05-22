"""
SQLModel table for storing configuration key-value pairs.
Values are encrypted before being written to the database.
"""

from typing import Optional
from sqlmodel import Field, SQLModel


class ConfigEntry(SQLModel, table=True):
    """One row per configuration key."""

    __tablename__ = "config_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True, max_length=128)
    # Value is stored as an encrypted string (Fernet token, base64-encoded)
    value_encrypted: str = Field(default="")
