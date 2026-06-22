import os
import pytest
from unittest.mock import patch, MagicMock


def test_get_store_returns_supabase_by_default(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")
    with patch("store.supabase_store.create_client", return_value=MagicMock()):
        from store import get_store
        from store.supabase_store import SupabaseStore
        import importlib, store
        importlib.reload(store)
        s = get_store()
        assert isinstance(s, SupabaseStore)


def test_get_store_returns_pinecone(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "pinecone")
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
    with patch("store.pinecone_store.Pinecone") as MockPC:
        MockPC.return_value.Index.return_value = MagicMock()
        from store import get_store
        from store.pinecone_store import PineconeStore
        import importlib, store
        importlib.reload(store)
        s = get_store()
        assert isinstance(s, PineconeStore)


def test_get_store_raises_on_unknown(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "weaviate")
    import importlib, store
    importlib.reload(store)
    with pytest.raises(ValueError, match="Unknown VECTOR_STORE"):
        from store import get_store
        get_store()
