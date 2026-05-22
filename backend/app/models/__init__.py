# Export all models so that SQLModel.metadata is populated when init_db() runs
from app.models.config import ConfigEntry          # noqa: F401
from app.models.indexing import IndexedDocument    # noqa: F401
from app.models.document import (                  # noqa: F401
    PaperlessDocument,
    PaperlessDocumentList,
    ConnectionTestResult,
)