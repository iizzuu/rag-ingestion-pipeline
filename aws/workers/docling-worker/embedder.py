import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor

import boto3

log = logging.getLogger(__name__)

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "eu-west-2"),
)
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.titan-embed-text-v2:0")
DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))


def _embed_one(text: str) -> list[float]:
    response = _bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({"inputText": text, "dimensions": DIMENSIONS, "normalize": True}),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


def embed_chunks(chunks: list[dict]) -> list[dict]:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        embeddings = list(executor.map(lambda c: _embed_one(c["text"]), chunks))
    return [{**chunk, "embedding": embedding} for chunk, embedding in zip(chunks, embeddings)]
