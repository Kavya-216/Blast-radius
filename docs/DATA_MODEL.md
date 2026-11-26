# Data Model

SQLite tables include repositories, source_documents, chunks, symbols, relationships, ingestion_jobs, and analyses.

- `source_documents` tracks content hash, source type, deletion state, and document version.
- `chunks` contain source-aware text and traceable metadata.
- `symbols` contain stable repository/file/qualified-name identifiers.
- `relationships` preserve source, target, type, evidence source, extraction method, and static evidence strength.
- `ingestion_jobs` track file and chunk counts plus success or failure.

Vector embeddings are calculated in memory. SQLite is the active metadata and chunk store; Chroma is not used in the current implementation.
