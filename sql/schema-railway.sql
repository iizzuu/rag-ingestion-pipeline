-- Document Ingestion Pipeline — Supabase Schema
-- Run in the Supabase SQL Editor before using the pipeline.
-- dialect: postgresql

CREATE EXTENSION IF NOT EXISTS vector;

-- document_embeddings: written by the ingestion pipeline
-- Compatible with LangChain SupabaseVectorStore
CREATE TABLE IF NOT EXISTS document_embeddings (
    id          BIGSERIAL PRIMARY KEY,
    chunk_id    TEXT UNIQUE NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1536)
);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Metadata filter index (document_id, heading_path, etc.)
CREATE INDEX IF NOT EXISTS document_embeddings_metadata_idx
    ON document_embeddings
    USING gin (metadata);

-- match_document_embeddings: RPC function for similarity search
-- Used by LangChain SupabaseVectorStore and direct pgvector queries
CREATE OR REPLACE FUNCTION match_document_embeddings (
    query_embedding  vector(1536),
    match_count      INT     DEFAULT 10,
    filter           JSONB   DEFAULT '{}'
)
RETURNS TABLE (
    id          BIGINT,
    chunk_id    TEXT,
    content     TEXT,
    metadata    JSONB,
    similarity  FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        document_embeddings.id,
        document_embeddings.chunk_id,
        document_embeddings.content,
        document_embeddings.metadata,
        1 - (document_embeddings.embedding <=> query_embedding) AS similarity
    FROM document_embeddings
    WHERE
        CASE
            WHEN filter = '{}' THEN TRUE
            ELSE document_embeddings.metadata @> filter
        END
    ORDER BY document_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
