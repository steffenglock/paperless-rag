# ── Stage 1: Build React frontend ───────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Kopiere die package.json und installiere die Abhängigkeiten frisch.
# 'npm install' fängt im CI-Runner unpassende oder fehlende Lock-Dateien ab.
COPY frontend/package.json ./
RUN npm install

# Kopiere den restlichen Frontend-Quellcode und baue die Produktions-Artefakte
COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python backend + final image ───────────────────
FROM python:3.12-slim AS final

# Installiere Nginx und Wget (wird für den Healthcheck im Entrypoint benötigt)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        wget \
    && rm -rf /var/lib/apt/lists/*

# ── Backend-Abhängigkeiten installieren ──────────────────────
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Backend-Quellcode
COPY backend/app ./app

# ── Frontend-Artefakte einbetten ─────────────────────────────
# Kopiert das fertig kompilierte Frontend aus Stage 1 in das finale Image
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# ── Nginx-Konfiguration einrichten ───────────────────────────
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Entferne die Standard-Nginx-Konfiguration, falls vorhanden
RUN rm -f /etc/nginx/sites-enabled/default

# ── Entrypoint einrichten ────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Mount-Punkt für die persistenten Daten (SQLite + ChromaDB)
VOLUME ["/app/data"]

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
