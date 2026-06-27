import os
import uuid
import logging
import tempfile
import threading

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from docling.document_converter import DocumentConverter

from chunker import chunk_document
from store import get_store

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 20
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}

S3_BUCKET = os.environ["S3_BUCKET"]
S3_PREFIX = os.environ.get("S3_PREFIX", "raw")

_status: dict[str, dict] = {}
_status_lock = threading.Lock()

_store = None
_openai_client = None
_converter = None
_s3_client = None


def _init_services():
    global _store, _openai_client, _converter, _s3_client
    if _store is None:
        _store = get_store()
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    if _converter is None:
        _converter = DocumentConverter()
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "eu-west-2"),
        )


@app.before_request
def ensure_services():
    _init_services()


def _upload_to_s3(tmp_path: str, document_id: str, filename: str) -> str:
    key = f"{S3_PREFIX}/{document_id}/{filename}"
    _s3_client.upload_file(tmp_path, S3_BUCKET, key)
    log.info("Uploaded raw file to s3://%s/%s", S3_BUCKET, key)
    return key


def _embed(chunks: list[dict]) -> list[dict]:
    embedded = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        response = _openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[c["text"] for c in batch],
        )
        for chunk, item in zip(batch, response.data):
            embedded.append({**chunk, "embedding": item.embedding})
    return embedded


def _process(document_id: str, tmp_path: str, filename: str) -> None:
    try:
        s3_key = _upload_to_s3(tmp_path, document_id, filename)
        result = _converter.convert(tmp_path)

        chunks = chunk_document(result.document, document_id)
        if not chunks:
            raise RuntimeError("No chunks produced")
        embedded = _embed(chunks)
        _store.upsert_chunks(embedded)
        status = {"status": "ready", "chunk_count": len(chunks)}
        if s3_key:
            status["s3_key"] = s3_key
        with _status_lock:
            _status[document_id] = status
        log.info("Done — %d chunks for %s", len(chunks), document_id)
    except Exception as e:
        log.error("Failed for %s: %s", document_id, e, exc_info=True)
        with _status_lock:
            _status[document_id] = {"status": "error", "error": str(e)}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/ingest")
def ingest():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    document_id = str(uuid.uuid4())
    filename = file.filename

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        file.save(tmp)
        tmp_path = tmp.name

    with _status_lock:
        _status[document_id] = {"status": "processing"}

    threading.Thread(target=_process, args=(document_id, tmp_path, filename), daemon=True).start()
    log.info("Received %s → documentId=%s", filename, document_id)
    return jsonify({"document_id": document_id, "status": "processing"})


@app.get("/api/documents")
def list_documents():
    with _status_lock:
        docs = [{"document_id": k, **v} for k, v in _status.items()]
    return jsonify({"documents": docs})


if __name__ == "__main__":
    _init_services()
    port = int(os.environ.get("PORT", 3008))
    app.run(host="0.0.0.0", port=port)
