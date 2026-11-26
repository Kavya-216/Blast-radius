# Implementation Status

## Baseline

- Existing workspace contains a partial baseline implementation of FastAPI, SQLite, ingestion, AST analysis, and retrieval.
- Baseline testing found and fixed an attribute-call AST gap and a nested-SQL connection ingestion defect.
- Python 3.14.2 and pip 26.2.2 are available.
- Current implementation uses FastAPI, Pydantic, SQLite, pytest, Streamlit, and deterministic hash vectors; no transformer model or Chroma store is active.

## Planned phases

1. Application foundation and SQLite health/status APIs.
2. Incremental local repository/document ingestion.
3. AST analysis and relationship graph.
4. Dense, BM25, hybrid, and graph-assisted retrieval.
5. RAG providers, structured reports, and citation validation.
6. Pull request and incident workflows.
7. Optional ML risk prediction and evaluation.
8. GitHub integration and webhook verification.
9. Streamlit interface.
10. Docker, CI, documentation, and independent audit.

## Actual status

- Implemented and tested: FastAPI foundation, SQLite, incremental local ingestion, source-aware chunking, AST symbols, relationships, BM25, hash dense retrieval, RRF, RAG evidence assembly, citation labels, abstention, PR report assembly, incident investigation, HMAC webhook verification, Streamlit UI, Docker and GitHub Actions.
- Implemented but not fully evaluated: graph traversal and end-to-end Streamlit behavior.
- Implemented: Public GitHub HTTPS connection and on-demand file retrieval without cloning through the API and Streamlit sidebar.
- Implemented: Read-only GitHub pull request diff retrieval for connected repositories, with size limits and diff evidence in PR reports.
- Not implemented: GitHub Check Run or PR comment publishing, and webhook event processing.
- Not implemented: active Chroma retrieval, hosted LLM generation, reranker, trained ML model, MLflow and gold retrieval benchmark.
- Synthetic data: clearly labelled in `data/sample_repository`, `data/sample_documents`, and `data/sample_incidents`.

## Active dependencies

- Runtime: FastAPI, Pydantic, Uvicorn, Streamlit.
- Testing: pytest and HTTPX.
- ML/vector-store dependencies will be added only when those features are implemented.
