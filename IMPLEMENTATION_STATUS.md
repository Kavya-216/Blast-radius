# Implementation Status

## Baseline

- Existing workspace contains a partial baseline implementation of FastAPI, SQLite, ingestion, AST analysis, and retrieval.
- Baseline validation is in progress; the first pass found an attribute-call AST gap and a nested-SQL connection ingestion defect.
- Python 3.14.2 and pip 26.2.2 are available.
- The implementation will use FastAPI, Pydantic, SQLite, pytest, Chroma where compatible, and Hugging Face-compatible embeddings.

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
- Partially implemented: GitHub REST client; no confirmed Check Run or PR comment publishing.
- Implemented: Public GitHub HTTPS connection and on-demand file retrieval without cloning through the API and Streamlit sidebar.
- Not implemented: active Chroma retrieval, hosted LLM generation, reranker, trained ML model, MLflow and gold retrieval benchmark.
- Synthetic data: clearly labelled in `data/sample_repository`, `data/sample_documents`, and `data/sample_incidents`.

## Dependency plan

- Runtime: FastAPI, Pydantic, Uvicorn, NumPy, Pandas, scikit-learn, Chroma, optional Hugging Face libraries.
- Testing: pytest and HTTPX.
- MLflow is optional and will only be added when a meaningful local experiment is implemented.
- The initial CPU implementation will avoid GPU requirements.
