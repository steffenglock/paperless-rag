# Import all routers here so main.py only needs one import
from app.api.routes.config import router as config_router        # noqa: F401
from app.api.routes.paperless import router as paperless_router  # noqa: F401
from app.api.routes.index import router as index_router          # noqa: F401
from app.api.routes.rag import router as rag_router              # noqa: F401
from app.api.routes.webhook import router as webhook_router      # noqa: F401