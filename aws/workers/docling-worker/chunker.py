import logging
from docling.chunking import HybridChunker

log = logging.getLogger(__name__)


def _extract_pages(chunk) -> list[int]:
    pages = set()
    for item in getattr(chunk.meta, "doc_items", []) or []:
        for prov in getattr(item, "prov", []) or []:
            page_no = getattr(prov, "page_no", None)
            if page_no is not None:
                pages.add(page_no)
    return sorted(pages)


def chunk_document(document, document_id: str, max_tokens: int = 512) -> list[dict]:
    chunker = HybridChunker(max_tokens=max_tokens)
    chunks = []
    for i, chunk in enumerate(chunker.chunk(document)):
        text = (chunk.text or "").strip()
        if not text:
            continue
        pages = _extract_pages(chunk)
        heading_path = chunk.meta.headings or []
        chunks.append({
            "chunk_id": f"{document_id}#{i}",
            "document_id": document_id,
            "text": text,
            "chunk_type": "section_text" if heading_path else "unstructured",
            "heading_path": heading_path,
            "parent_heading": (
                heading_path[-2] if len(heading_path) >= 2
                else (heading_path[0] if heading_path else None)
            ),
            "sequence": i,
            "page_start": min(pages) if pages else None,
            "page_end": max(pages) if pages else None,
            "estimated_token_count": len(text.split()),
        })
    return chunks
