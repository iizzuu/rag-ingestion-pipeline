import os
from pinecone import Pinecone
from .base import VectorStore


class PineconeStore(VectorStore):
    def __init__(self):
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self._index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

    def upsert_chunks(self, chunks: list[dict]) -> None:
        vectors = [
            {
                "id": c["chunk_id"],
                "values": c["embedding"],
                "metadata": {
                    k: c[k]
                    for k in (
                        "document_id", "text", "chunk_type",
                        "heading_path", "parent_heading", "sequence",
                        "page_start", "page_end", "estimated_token_count",
                    )
                },
            }
            for c in chunks
        ]
        self._index.upsert(vectors=vectors)
