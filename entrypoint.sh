#!/bin/sh
# Container entrypoint: start FastAPI backend, then Nginx in the foreground.

set -e

echo "==> Starting Paperless RAG backend (uvicorn) …"
cd /app/backend
uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --log-level "$(echo ${LOG_LEVEL:-info} | tr '[:upper:]' '[:lower:]')" &

echo "==> Waiting for backend to be ready …"
# Simple retry loop – avoids nginx 502 on cold starts
for i in $(seq 1 20); do
    if wget -q -O- http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "==> Backend is ready."
        break
    fi
    echo "    … attempt $i/20"
    sleep 1
done

echo "==> Starting Nginx …"
nginx -g "daemon off;"
