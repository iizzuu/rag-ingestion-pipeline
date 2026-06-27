from unittest.mock import MagicMock, patch
import pytest


def _make_store():
    with patch.dict("os.environ", {
        "OPENSEARCH_ENDPOINT": "https://test.us-east-1.aoss.amazonaws.com",
        "OPENSEARCH_INDEX": "test-index",
        "EMBEDDING_DIMENSIONS": "4",
        "AWS_REGION": "eu-west-2",
    }):
        with patch("store.opensearch_store.boto3.Session") as mock_session, \
             patch("store.opensearch_store.AWSV4SignerAuth"), \
             patch("store.opensearch_store.OpenSearch") as mock_os_cls:

            mock_session.return_value.get_credentials.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.indices.exists.return_value = True  # skip index creation
            mock_os_cls.return_value = mock_client

            from store.opensearch_store import OpenSearchStore
            store = OpenSearchStore()
            return store, mock_client


def test_upsert_chunks_calls_bulk():
    store, mock_client = _make_store()
    chunks = [
        {
            "chunk_id": "doc1#0",
            "document_id": "doc1",
            "text": "hello world",
            "embedding": [0.1, 0.2, 0.3, 0.4],
            "chunk_type": "section_text",
            "heading_path": ["Intro"],
            "parent_heading": "Intro",
            "sequence": 0,
            "page_start": 1,
            "page_end": 1,
            "estimated_token_count": 2,
        }
    ]

    store.upsert_chunks(chunks)

    mock_client.bulk.assert_called_once()
    body = mock_client.bulk.call_args.kwargs["body"]
    assert body[0] == {"index": {"_index": "test-index", "_id": "doc1#0"}}
    assert body[1]["text"] == "hello world"
    assert body[1]["embedding"] == [0.1, 0.2, 0.3, 0.4]


def test_upsert_chunks_sends_all_chunks():
    store, mock_client = _make_store()
    chunks = [
        {
            "chunk_id": f"doc1#{i}", "document_id": "doc1", "text": f"chunk {i}",
            "embedding": [0.1] * 4, "chunk_type": "unstructured", "heading_path": [],
            "parent_heading": None, "sequence": i, "page_start": None,
            "page_end": None, "estimated_token_count": 2,
        }
        for i in range(3)
    ]

    store.upsert_chunks(chunks)

    body = mock_client.bulk.call_args.kwargs["body"]
    # Each chunk produces 2 entries (action + document)
    assert len(body) == 6
    ids = [body[i]["index"]["_id"] for i in range(0, 6, 2)]
    assert ids == ["doc1#0", "doc1#1", "doc1#2"]


def test_ensure_index_creates_when_missing():
    with patch.dict("os.environ", {
        "OPENSEARCH_ENDPOINT": "https://test.us-east-1.aoss.amazonaws.com",
        "OPENSEARCH_INDEX": "new-index",
        "EMBEDDING_DIMENSIONS": "4",
        "AWS_REGION": "eu-west-2",
    }):
        with patch("store.opensearch_store.boto3.Session") as mock_session, \
             patch("store.opensearch_store.AWSV4SignerAuth"), \
             patch("store.opensearch_store.OpenSearch") as mock_os_cls:

            mock_session.return_value.get_credentials.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.indices.exists.return_value = False  # index does not exist
            mock_os_cls.return_value = mock_client

            from store.opensearch_store import OpenSearchStore
            OpenSearchStore()

            mock_client.indices.create.assert_called_once()
            call_kwargs = mock_client.indices.create.call_args.kwargs
            assert call_kwargs["index"] == "new-index"
            props = call_kwargs["body"]["mappings"]["properties"]
            assert props["embedding"]["type"] == "knn_vector"
            assert props["embedding"]["dimension"] == 4
