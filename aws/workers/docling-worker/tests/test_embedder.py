from unittest.mock import patch, MagicMock
import json


def _mock_bedrock_response(embedding):
    mock_response = MagicMock()
    mock_response["body"].read.return_value = json.dumps({"embedding": embedding}).encode()
    return mock_response


def test_embed_chunks_returns_embeddings():
    from embedder import embed_chunks

    chunks = [
        {"chunk_id": "doc#0", "text": "hello world", "sequence": 0},
        {"chunk_id": "doc#1", "text": "foo bar", "sequence": 1},
    ]
    fake_embedding = [0.1] * 1024

    with patch("embedder._bedrock") as mock_bedrock:
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({"embedding": fake_embedding}).encode())
        }
        result = embed_chunks(chunks)

    assert len(result) == 2
    assert result[0]["embedding"] == fake_embedding
    assert result[0]["chunk_id"] == "doc#0"
    assert result[1]["chunk_id"] == "doc#1"


def test_embed_chunks_preserves_all_fields():
    from embedder import embed_chunks

    chunks = [{"chunk_id": "doc#0", "text": "test", "heading_path": ["A", "B"], "sequence": 0}]
    fake_embedding = [0.5] * 1024

    with patch("embedder._bedrock") as mock_bedrock:
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({"embedding": fake_embedding}).encode())
        }
        result = embed_chunks(chunks)

    assert result[0]["heading_path"] == ["A", "B"]
    assert "embedding" in result[0]
