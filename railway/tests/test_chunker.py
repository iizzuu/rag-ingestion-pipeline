from unittest.mock import MagicMock, patch
import pytest

def _make_mock_chunk(text, headings, pages):
    chunk = MagicMock()
    chunk.text = text
    chunk.meta.headings = headings
    doc_item = MagicMock()
    prov = MagicMock()
    prov.page_no = pages[0] if pages else None
    doc_item.prov = [prov]
    chunk.meta.doc_items = [doc_item]
    return chunk


def test_chunk_document_section_text():
    from chunker import chunk_document

    mock_doc = MagicMock()
    mock_chunk = _make_mock_chunk(
        "Eligibility Criteria\nOnly claims arising from...",
        ["Claims Procedure", "Eligibility Criteria"],
        [4],
    )
    with patch("chunker.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = [mock_chunk]
        chunks = chunk_document(mock_doc, "doc_001")

    assert len(chunks) == 1
    c = chunks[0]
    assert c["chunk_id"] == "doc_001#0"
    assert c["document_id"] == "doc_001"
    assert c["chunk_type"] == "section_text"
    assert c["heading_path"] == ["Claims Procedure", "Eligibility Criteria"]
    assert c["parent_heading"] == "Claims Procedure"
    assert c["sequence"] == 0
    assert c["page_start"] == 4
    assert c["page_end"] == 4


def test_chunk_document_unstructured():
    from chunker import chunk_document

    mock_doc = MagicMock()
    mock_chunk = _make_mock_chunk("Some unstructured text.", [], [1])
    with patch("chunker.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = [mock_chunk]
        chunks = chunk_document(mock_doc, "doc_002")

    assert chunks[0]["chunk_type"] == "unstructured"
    assert chunks[0]["heading_path"] == []
    assert chunks[0]["parent_heading"] is None


def test_chunk_document_skips_empty_text():
    from chunker import chunk_document

    mock_doc = MagicMock()
    mock_chunk = _make_mock_chunk("   ", [], [])
    with patch("chunker.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = [mock_chunk]
        chunks = chunk_document(mock_doc, "doc_003")

    assert chunks == []


def test_parent_heading_single_level():
    from chunker import chunk_document

    mock_doc = MagicMock()
    mock_chunk = _make_mock_chunk("text", ["Top Level"], [2])
    with patch("chunker.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = [mock_chunk]
        chunks = chunk_document(mock_doc, "doc_004")

    assert chunks[0]["parent_heading"] == "Top Level"
