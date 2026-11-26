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
No hosted LLM is called. The offline provider selects relevant explanatory sentences from retrieved repository text; for architecture questions, it can also summarize layer dimensions from tables with explicit layer/input/output columns. It does not freely paraphrase or inject repository-specific architecture claims. Markdown lines that start with cross-references such as "See Component..." and code-like lines are excluded from summaries. It abstains when evidence is empty or contains no suitable prose. Citation validation compares labels in the response with evidence labels.
