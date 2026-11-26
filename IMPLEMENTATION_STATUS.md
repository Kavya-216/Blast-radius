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

## Dependency plan

- Runtime: FastAPI, Pydantic, Uvicorn, NumPy, Pandas, scikit-learn, Chroma, optional Hugging Face libraries.
- Testing: pytest and HTTPX.
- MLflow is optional and will only be added when a meaningful local experiment is implemented.
- The initial CPU implementation will avoid GPU requirements.
