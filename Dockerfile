# ── Stage 1: Build React frontend ───────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python backend + final image ───────────────────
FROM python:3.12-slim AS final

# Install nginx and wget (used in entrypoint health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        wget \
    && rm -rf /var/lib/apt/lists/*

# ── Backend dependencies ─────────────────────────────────────
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/app ./app

# ── Frontend artifacts ───────────────────────────────────────
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# ── Nginx config ─────────────────────────────────────────────
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

# ── Entrypoint ───────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Runtime data volume (SQLite + ChromaDB)
VOLUME ["/app/data"]

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
