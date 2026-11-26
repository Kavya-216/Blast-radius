# RAG Design

## Chunking
Python files are chunked around classes and functions. Markdown is split by headings. Plain text is split by paragraphs.

## Embeddings
The implementation uses a deterministic 128-dimension hash vector. It is a reproducible offline baseline, not a semantic transformer embedding.

## Dense and sparse retrieval
Dense retrieval ranks normalized cosine similarity. BM25 ranks term matching with document-length normalization.

## Hybrid retrieval
Dense and sparse rankings are combined using Reciprocal Rank Fusion. RRF is robust to incompatible raw scores.

## Graph assistance
Graph traversal finds bounded static relationships around retrieved symbols. It is labelled as static evidence and does not prove runtime control flow.

## Generation and abstention
No hosted LLM is called. The offline provider returns retrieved excerpts, explicitly labels the provider, and abstains when evidence is empty. Citation validation compares labels in the response with evidence labels.
