import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from .base import VectorStore

class QdrantStore(VectorStore):
    def __init__(self):
        self._client = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
        self._collection = os.environ["QDRANT_COLLECTION"]

    def upsert_chunks(self, chunks: list[dict]) -> None:
        points = [
            PointStruct(
                id=c["sequence"],
                vector=c["embedding"],
                payload={
                    k: c[k]
                    for k in (
                        "chunk_id", "document_id", "text", "chunk_type",
                        "heading_path", "parent_heading", "sequence",
                        "page_start", "page_end", "estimated_token_count",
                    )
                },
            )
            for c in chunks
        ]
        self._client.upsert(collection_name=self._collection, points=points)
