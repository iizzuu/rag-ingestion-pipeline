import os
from .base import VectorStore


def get_store() -> VectorStore:
    name = os.environ.get("VECTOR_STORE", "supabase").lower()
    if name == "supabase":
        from .supabase_store import SupabaseStore
        return SupabaseStore()
    if name == "pinecone":
        from .pinecone_store import PineconeStore
        return PineconeStore()
    if name == "qdrant":
        from .qdrant_store import QdrantStore
        return QdrantStore()
    raise ValueError(f"Unknown VECTOR_STORE: {name!r}. Choose: supabase, pinecone, qdrant")
