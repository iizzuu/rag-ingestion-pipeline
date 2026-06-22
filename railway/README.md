# Railway Deployment

Single Flask process. Zero cloud infrastructure required.

## Prerequisites

- Python 3.11+
- OpenAI API key
- A vector store (Supabase, Pinecone, or Qdrant)

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python server.py
```

## Deploy to Railway

1. Fork this repo
2. In Railway: New Project → Deploy from GitHub → select `document-ingestion-pipeline`
3. Set root directory to `railway/`
4. Add env vars from `.env.example`
5. Railway detects the Dockerfile and deploys

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/ingest` | Upload a file (multipart/form-data, field name: `file`) |
| GET | `/api/documents` | List all ingested documents and their status |
| GET | `/health` | Health check |

## Swap your vector store

Change `VECTOR_STORE` to `pinecone` or `qdrant` and add the corresponding env vars.
Nothing else changes.

## Supported file types

PDF, DOCX, TXT, MD, CSV, JSON
