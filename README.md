# Document Ingestion Pipeline

A production-grade document ingestion pipeline that parses, hierarchically chunks, embeds, and stores documents in any vector store. Built to be forked and dropped into your stack.

```
Upload → Parse (Docling) → Chunk (HybridChunker) → Embed → Store
```

Swap your vector store with one environment variable. Nothing else changes.

---

## How it works

### 1. Parse

Documents are parsed with [Docling](https://github.com/DS4SD/docling), which understands PDF structure, reading order, tables, and heading hierarchy. Output is a structured document object — not raw text.

### 2. Chunk (hierarchically)

The Docling `HybridChunker` splits documents by structure, not by token count. Each chunk carries its full heading ancestry:

```json
{
  "chunk_id": "doc_abc#3",
  "document_id": "doc_abc",
  "text": "Only claims arising from covered perils...",
  "chunk_type": "section_text",
  "heading_path": ["Claims Procedure", "Eligibility Criteria"],
  "parent_heading": "Claims Procedure",
  "sequence": 3,
  "page_start": 4,
  "page_end": 5,
  "estimated_token_count": 287
}
```

A chunk from `Eligibility Criteria` knows it belongs to `Claims Procedure`. It is not an orphan fragment.

### 3. Embed

Chunks are embedded into dense vectors:
- **Railway**: OpenAI `text-embedding-3-small` (1536 dims)
- **AWS**: Bedrock Titan Embed v2 (1024 dims, concurrent)

### 4. Store

Vectors are upserted into your vector store. Switch stores by changing one env var:

```bash
VECTOR_STORE=supabase   # default — pgvector
VECTOR_STORE=pinecone
VECTOR_STORE=qdrant
```

---

## Retrieval pattern

After ingestion, query your vector store for the top-k chunks closest to your query embedding. Then expand context by fetching sibling chunks — every chunk under the same heading:

```sql
-- Supabase: fetch all chunks in the same section
SELECT content, metadata
FROM document_embeddings
WHERE metadata->>'document_id' = 'doc_abc'
  AND metadata->>'parent_heading' = 'Claims Procedure'
ORDER BY (metadata->>'sequence')::int;
```

Concatenate the sibling chunks in sequence order. Pass the assembled context to your LLM:

```python
context = "\n\n".join(chunk["content"] for chunk in siblings)

response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Answer using only the context provided."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ],
)
```

The model receives the complete section, not a fragment.

---

## Deployments

| Target | Stack | Status |
|---|---|---|
| [Railway](./railway/) | Flask + OpenAI + any vector store | Ready |
| [AWS](./aws/) | ECS Fargate + Bedrock + Terraform + CDK | Ready |
| [Azure](./azure/) | Blob Storage + Service Bus + ACI | Coming soon |
| [GCP](./gcp/) | GCS + Pub/Sub + Cloud Run | Coming soon |

---

## Swap your vector store

Every deployment uses the same pattern. Set `VECTOR_STORE` in your environment:

| Value | Store | Extra env vars needed |
|---|---|---|
| `supabase` | Supabase pgvector (default) | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| `pinecone` | Pinecone | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` |
| `qdrant` | Qdrant | `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_API_KEY` |

The chunker, parser, and embedding logic do not change.

---

## Chunk schema reference

Every chunk written to the vector store carries these fields in `metadata`:

| Field | Type | Description |
|---|---|---|
| `chunk_id` | string | Unique ID: `{document_id}#{sequence}` |
| `document_id` | string | Groups all chunks for a document |
| `chunk_type` | string | `section_text` or `unstructured` |
| `heading_path` | string[] | Full heading ancestry from root |
| `parent_heading` | string \| null | Immediate parent section |
| `sequence` | integer | Position in document |
| `page_start` | integer \| null | Start page |
| `page_end` | integer \| null | End page |
| `estimated_token_count` | integer | Approximate word count |

---

## Technologies

| Component | Technology |
|---|---|
| PDF/DOCX parsing | Docling (DS4SD) |
| Hierarchical chunking | Docling HybridChunker |
| Embeddings (Railway) | OpenAI text-embedding-3-small |
| Embeddings (AWS) | Bedrock Titan Embed v2 |
| Default vector store | Supabase pgvector |
| IaC | Terraform ≥ 1.7 + AWS CDK v2 |
| Railway runtime | Python 3.11, Flask, Gunicorn |
| AWS runtime | ECS Fargate (Python), Lambda (Node.js 20) |
