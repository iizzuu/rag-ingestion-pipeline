import os
from .base import VectorStore
from .supabase_store import SupabaseStore
from .pinecone_store import PineconeStore
from .qdrant_store import QdrantStore


def get_store() -> VectorStore:
    name = os.environ.get("VECTOR_STORE", "supabase").lower()
    if name == "supabase":
        return SupabaseStore()
    if name == "pinecone":
        return PineconeStore()
    if name == "qdrant":
        return QdrantStore()
    raise ValueError(f"Unknown VECTOR_STORE: {name!r}. Choose: supabase, pinecone, qdrant")
