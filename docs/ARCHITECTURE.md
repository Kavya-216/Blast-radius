# Architecture

ImpactLens is a modular monolith. FastAPI receives repository, RAG, incident, PR, and webhook requests. SQLite stores repositories, documents, chunks, symbols, relationships, jobs, and analyses.

## Ingestion
Files are discovered, hashed, and compared with stored content hashes. Unchanged documents are not re-chunked or re-written. Changed documents receive new chunks and versions. Missing documents are marked deleted and their chunks removed.

## Analysis
Python source uses `ast` to extract classes, functions, imports, and calls. Relationship records preserve evidence source and extraction method. Traversal is bounded and bidirectional in memory.

## Retrieval
BM25 provides sparse ranking. Offline hash embeddings provide dense cosine ranking. RRF combines rankings. Graph neighbors can supplement evidence. SQLite is the active metadata store; Chroma is not used by the current local retrieval path.

## Generation
The offline provider assembles a labelled evidence summary. It abstains when no chunks are found. Citations are checked against retrieved chunk labels.

## Storage and failure handling
Ingestion creates a running job and marks the repository failed if an exception occurs. There is no partial publication mechanism: new index versions and status are committed together.
