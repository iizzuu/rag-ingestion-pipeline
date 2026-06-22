import os
from supabase import create_client, Client
from .base import VectorStore


class SupabaseStore(VectorStore):
    def __init__(self):
        self._client: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )

    def upsert_chunks(self, chunks: list[dict]) -> None:
        records = [
            {
                "chunk_id": c["chunk_id"],
                "content": c["text"],
                "embedding": c["embedding"],
                "metadata": {
                    k: c[k]
                    for k in (
                        "chunk_id", "document_id", "chunk_type",
                        "heading_path", "parent_heading", "sequence",
                        "page_start", "page_end", "estimated_token_count",
                    )
                },
            }
            for c in chunks
        ]
        self._client.table("document_embeddings").upsert(
            records, on_conflict="chunk_id"
        ).execute()
