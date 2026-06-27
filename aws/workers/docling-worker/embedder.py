import json
import os
import logging
import time
import random
from botocore.exceptions import ClientError

import boto3

log = logging.getLogger(__name__)

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION", "eu-west-2"),
)

PRIMARY_MODEL   = os.environ.get("BEDROCK_MODEL_ID", "amazon.titan-embed-text-v2:0")
FALLBACK_MODEL  = os.environ.get("BEDROCK_FALLBACK_MODEL_ID", "cohere.embed-english-v3")
DIMENSIONS      = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
REQUEST_DELAY   = float(os.environ.get("REQUEST_DELAY", "0.5"))


def _invoke_titan(text: str) -> list[float]:
    response = _bedrock.invoke_model(
        modelId=PRIMARY_MODEL,
        body=json.dumps({"inputText": text, "dimensions": DIMENSIONS, "normalize": True}),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


def _invoke_cohere(text: str) -> list[float]:
    response = _bedrock.invoke_model(
        modelId=FALLBACK_MODEL,
        body=json.dumps({"texts": [text], "input_type": "search_document"}),
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embeddings"][0]


def _embed_one(text: str, use_titan: bool) -> tuple[list[float], bool]:
    """Returns (embedding, titan_still_available)."""
    if use_titan:
        for attempt in range(2):
            try:
                return _invoke_titan(text), True
            except ClientError as e:
                if e.response["Error"]["Code"] != "ThrottlingException":
                    raise
                wait = (2 ** attempt) + random.uniform(0, 1)
                log.warning("Titan throttled, retrying in %.1fs (attempt %d/2)", wait, attempt + 1)
                time.sleep(wait)
        log.warning("Titan unavailable, falling back to Cohere for remainder of batch")

    return _invoke_cohere(text), False


def embed_chunks(chunks: list[dict]) -> list[dict]:
    embeddings = []
    use_titan = True
    for i, chunk in enumerate(chunks):
        embedding, use_titan = _embed_one(chunk["text"], use_titan)
        embeddings.append(embedding)
        if i < len(chunks) - 1:
            time.sleep(REQUEST_DELAY)
    return [{**chunk, "embedding": embedding} for chunk, embedding in zip(chunks, embeddings)]
