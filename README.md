# Document Ingestion Pipeline

**GitHub:** [github.com/iizzuu/rag-ingestion-pipeline](https://github.com/iizzuu/rag-ingestion-pipeline)

This is a production-ready document ingestion pipeline that takes raw files, parses them, breaks them into structured chunks, generates vector embeddings, and stores everything ready for retrieval. You can deploy it on Railway for a simple cloud setup or on AWS for a fully serverless, event-driven architecture.

The core flow is the same regardless of where you deploy it:

```
Upload a document → Parse with Docling → Chunk by structure → Embed → Store
```

## How it works

### Parsing

Documents are parsed using [Docling](https://github.com/DS4SD/docling), which understands the actual structure of a PDF or DOCX file. It reads heading hierarchy, table layouts, and reading order rather than just dumping raw text. The output is a structured document object that the chunker can work with meaningfully.

### Chunking

The chunker uses Docling's HybridChunker to split documents by their natural structure rather than cutting at arbitrary token limits. Every chunk produced carries its full heading ancestry so you always know where in the document it came from.

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

A chunk from the Eligibility Criteria section knows it belongs to the Claims Procedure section. When you retrieve it later, you have the context to expand into surrounding chunks from the same section.

### Embedding

Both deployments generate dense vector embeddings, but use different providers suited to their environment.

The Railway deployment uses OpenAI text-embedding-3-small at 1536 dimensions. The AWS deployment uses Amazon Bedrock Titan Embed v2 at 1024 dimensions, with Cohere Embed as an automatic fallback if Titan is throttled.

### Storage

Raw files are uploaded to S3 before processing begins so the original document is always preserved regardless of what happens during conversion. The chunks and embeddings go into the vector store.

## Deployments

| Target | Stack | Status |
|---|---|---|
| [Railway](./railway/) | Flask, OpenAI, Supabase, S3 | Ready |
| [AWS](./aws/) | ECS Fargate, Bedrock, OpenSearch Serverless, Terraform | Ready |
| [Azure](./azure/) | Blob Storage, Service Bus, ACI | Coming soon |
| [GCP](./gcp/) | GCS, Pub/Sub, Cloud Run | Coming soon |

## Querying after ingestion

Once documents are ingested, you query the vector store for the chunks most semantically similar to your question. Because every chunk carries its heading path, you can then expand context by fetching all sibling chunks from the same section.

```sql
SELECT content, metadata
FROM document_embeddings
WHERE metadata->>'document_id' = 'doc_abc'
  AND metadata->>'parent_heading' = 'Claims Procedure'
ORDER BY (metadata->>'sequence')::int;
```

Concatenate the siblings in order and pass them to your language model. The model gets the full section rather than a fragment.

## Chunk fields reference

| Field | Type | Description |
|---|---|---|
| chunk_id | string | Unique ID in the format document_id followed by sequence number |
| document_id | string | Groups all chunks belonging to one document |
| chunk_type | string | Either section_text or unstructured |
| heading_path | string array | Full heading ancestry from the document root |
| parent_heading | string or null | The immediate parent section |
| sequence | integer | Position of this chunk within the document |
| page_start | integer or null | Page where the chunk begins |
| page_end | integer or null | Page where the chunk ends |
| estimated_token_count | integer | Approximate word count |

## Technology stack

| Component | Technology |
|---|---|
| Document parsing | Docling by DS4SD |
| Chunking | Docling HybridChunker |
| Embeddings on Railway | OpenAI text-embedding-3-small |
| Embeddings on AWS | Bedrock Titan Embed v2 with Cohere fallback |
| Vector store on Railway | Supabase pgvector |
| Vector store on AWS | OpenSearch Serverless |
| Raw file storage | Amazon S3 |
| AWS infrastructure | Terraform and AWS CDK v2 |
| Railway runtime | Python 3.11, Flask, Gunicorn |
| AWS runtime | ECS Fargate (Python 3.11), Lambda (Node.js 20) |
