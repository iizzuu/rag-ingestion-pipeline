import io
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    with patch("server.get_store", return_value=MagicMock()), \
         patch("server.OpenAI", return_value=MagicMock()), \
         patch("server.DocumentConverter", return_value=MagicMock()):
        import server
        server.app.config["TESTING"] = True
        with server.app.test_client() as c:
            yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_ingest_no_file(client):
    resp = client.post("/api/ingest")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_ingest_unsupported_type(client):
    data = {"file": (io.BytesIO(b"data"), "file.exe")}
    resp = client.post("/api/ingest", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "Unsupported" in resp.get_json()["error"]


def test_ingest_valid_file_returns_document_id(client):
    data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "test.pdf")}
    with patch("server.threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        resp = client.post("/api/ingest", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "document_id" in body
    assert body["status"] == "processing"


def test_list_documents_empty(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert "documents" in resp.get_json()
