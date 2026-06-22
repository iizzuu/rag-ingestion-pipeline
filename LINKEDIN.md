# LinkedIn Post

---

Most RAG pipelines chunk documents by token count.

That's the wrong unit.

A clause that sits under a sub-condition of an exception is not the
same as a standalone clause. A section that only applies to a specific
endorsement is not the same as a top-level term. If your chunker
doesn't understand document structure, your retrieval system doesn't
either — and neither does your model.

I built an open-source document ingestion pipeline that solves this at
the chunking layer.

Instead of splitting by token count, it uses Docling's HybridChunker to
preserve the full heading hierarchy through the entire pipeline. Every
chunk that reaches your vector store carries its complete ancestry:

  ["Claims Procedure", "Eligibility Criteria"]

When retrieval returns a chunk, you query its siblings — every other
chunk under the same heading — reassemble the full section in sequence
order, and pass it to your model. Not a fragment. Context.

The pipeline is built to be forked. Pick your deployment target, set
one env var to select your vector store, and it runs:

→ Railway: single Flask process, zero cloud infrastructure, live in
  under 10 minutes
→ AWS: ECS Fargate + SQS + Lambda, full Terraform stack and CDK
  alternative included — terraform apply and you're done
→ Azure and GCP coming next

Supabase, Pinecone, and Qdrant implementations ship out of the box.
Swap stores by changing VECTOR_STORE. Nothing else moves.

[link to repo]

#RAG #LLM #CloudEngineering #AWS #Terraform #Python #OpenSource
#MachineLearning #DocumentAI
