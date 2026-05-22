# Paperless RAG

> RAG-powered semantic search for your [Paperless-ngx](https://docs.paperless-ngx.com) documents.

## Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.12 · FastAPI · SQLite · ChromaDB |
| Frontend   | React 18 · Vite · TypeScript · TailwindCSS |
| Container  | Single Docker container (amd64 + arm64) |
| LLM        | Ollama / OpenAI-compatible APIs         |

## Quick Start

```bash
cp .env.example .env
# Edit .env with your Paperless-ngx URL and token

docker compose up -d
# Open http://localhost:3000
```

## Development

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Configuration

See `.env.example` for all available environment variables.

## License

MIT
