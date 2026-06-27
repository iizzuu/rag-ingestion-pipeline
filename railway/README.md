# Railway Deployment

This is the lightweight version of the pipeline. It runs as a single Flask process and does not require any cloud infrastructure beyond what you already have. Upload a file, get back a document ID, and the server handles everything else in the background.

## How it works

You send a file to the ingest endpoint. The server saves it to a temporary file, uploads the original to S3 for permanent storage, then kicks off background processing. Docling converts the document, the chunker splits it by structure, OpenAI generates embeddings for each chunk, and Supabase stores them. The temporary file is deleted after processing regardless of whether it succeeded or failed.

## What you need

You will need Python 3.11 or higher, an OpenAI API key, a Supabase project, and an AWS account with an S3 bucket for raw file storage. S3 storage is required, not optional. An ingestion pipeline that does not keep the original document is not production-ready.

## Running locally

```bash
cd railway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open the .env file and fill in your keys, then start the server:

```bash
python3 server.py
```

The server starts on port 3008 by default. You can change this with the PORT variable.

## Environment variables

```
OPENAI_API_KEY         Your OpenAI API key
VECTOR_STORE           Set to supabase
SUPABASE_URL           Your Supabase project URL
SUPABASE_SERVICE_KEY   Your Supabase service role key
S3_BUCKET              The S3 bucket name for raw file storage
AWS_REGION             The AWS region your bucket is in
AWS_ACCESS_KEY_ID      Your AWS access key
AWS_SECRET_ACCESS_KEY  Your AWS secret key
PORT                   Port to run on, defaults to 3008
```

## Deploying to Railway

Fork this repository, then in the Railway dashboard create a new project and connect it to your GitHub repo. Set the root directory to railway/ and add your environment variables. Railway will detect the Dockerfile automatically and handle the rest.

## Endpoints

**POST /api/ingest**

Upload a document using multipart form data with the field name set to file. The server responds immediately with a document ID and starts processing in the background.

```bash
curl -X POST http://localhost:3008/api/ingest -F "file=@your-document.pdf"
```

Response:
```json
{
  "document_id": "abc-123",
  "status": "processing"
}
```

**GET /api/documents**

Returns the status of all documents processed since the server started.

```bash
curl http://localhost:3008/api/documents
```

When a document finishes processing the status changes to ready and includes the chunk count and the S3 key where the original file is stored.

**GET /health**

Returns a simple ok response. Useful for uptime checks.

## Supported file types

PDF, DOCX, TXT, MD, CSV and JSON.
