import os
import logging

import boto3
from docling.document_converter import DocumentConverter

from chunker import chunk_document
from embedder import embed_chunks
from store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3")
converter = DocumentConverter()


def run():
    bucket = os.environ["BUCKET"]
    key = os.environ["KEY"]
    document_id = os.environ["DOCUMENT_ID"]

    file_name = key.split("/")[-1]
    file_path = f"/tmp/{document_id}_{file_name}"

    try:
        log.info("Downloading s3://%s/%s", bucket, key)
        s3.download_file(bucket, key, file_path)
        result = converter.convert(file_path)
    except Exception as e:
        raise RuntimeError(f"Conversion failed for {document_id}: {e}") from e
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    chunks = chunk_document(result.document, document_id)
    if not chunks:
        raise RuntimeError(f"No chunks produced for {document_id}")

    embedded = embed_chunks(chunks)
    store = get_store()
    store.upsert_chunks(embedded)
    log.info("Done — %d chunks for %s", len(embedded), document_id)


if __name__ == "__main__":
    run()
