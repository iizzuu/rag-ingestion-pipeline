import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

from .base import VectorStore


class OpenSearchStore(VectorStore):
    def __init__(self):
        endpoint = os.environ["OPENSEARCH_ENDPOINT"].replace("https://", "")
        region = os.environ.get("AWS_REGION", "eu-west-2")
        self._index = os.environ.get("OPENSEARCH_INDEX", "document-chunks")
        self._dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))

        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, "aoss")

        self._client = OpenSearch(
            hosts=[{"host": endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
        self._ensure_index()

    def _ensure_index(self) -> None:
        if self._client.indices.exists(index=self._index):
            return
        self._client.indices.create(
            index=self._index,
            body={
                "settings": {"index.knn": True},
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self._dimensions,
                            "method": {
                                "name": "hnsw",
                                "space_type": "innerproduct",
                                "engine": "faiss",
                            },
                        },
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "text": {"type": "text"},
                        "chunk_type": {"type": "keyword"},
                        "heading_path": {"type": "keyword"},
                        "parent_heading": {"type": "keyword"},
                        "sequence": {"type": "integer"},
                        "page_start": {"type": "integer"},
                        "page_end": {"type": "integer"},
                        "estimated_token_count": {"type": "integer"},
                    }
                },
            },
        )

    def upsert_chunks(self, chunks: list[dict]) -> None:
        body = []
        for c in chunks:
            body.append({"index": {"_index": self._index, "_id": c["chunk_id"]}})
            body.append({
                k: c[k]
                for k in (
                    "embedding", "chunk_id", "document_id", "text", "chunk_type",
                    "heading_path", "parent_heading", "sequence",
                    "page_start", "page_end", "estimated_token_count",
                )
            })
        self._client.bulk(body=body)
