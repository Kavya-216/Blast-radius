# ImpactLens

ImpactLens is an evidence-grounded local prototype for software change impact analysis. It combines Python AST analysis, a lightweight SQL-backed relationship graph, dense and BM25 retrieval, reciprocal rank fusion, incident investigation, and structured PR-style reports.

This is a decision-support tool. It does not prove every dependency or predict every regression.

## Features

- FastAPI backend with health, repository, retrieval, RAG, PR, and incident endpoints.
- Incremental repository and document ingestion with content hashes.
- Source-aware chunking for Python, Markdown, and text.
- Python AST symbols, imports, function calls, and graph relationships.
- 128-dimension offline deterministic embeddings and BM25 hybrid retrieval.
- Reciprocal Rank Fusion and graph traversal.
- Deterministic offline RAG with abstention and citation validation.
- Optional HMAC-verified GitHub webhook endpoint.
- Streamlit demonstration interface.
- Optional ML prediction: explicitly unavailable until a valid labelled model exists.
- SQLite metadata and content persistence.

## Architecture

GitHub/local repository -> FastAPI -> ingestion -> SQLite/Chroma-compatible retrieval metadata -> AST/graph -> hybrid retrieval -> evidence assembly -> report or abstention.

## Setup

```bash
python -m pip install -r requirements.txt
python scripts/run_demo.py
uvicorn app.main:app --reload
```

Demo UI:

```bash
streamlit run frontend/streamlit_app.py
```

API docs: `http://127.0.0.1:8000/docs`

## Demo

The sample repository, incidents, and architecture documents are synthetic and explicitly labelled as demo data.

```bash
python scripts/run_demo.py
```

## API

- `GET /health`
- `POST /repositories`
- `GET /repositories/{id}`
- `POST /repositories/{id}/index`
- `GET /repositories/{id}/retrieve?query=...`
- `POST /rag/query`
- `POST /prs/analyze`
- `POST /incidents/investigate`
- `POST /webhooks/github`

## Configuration

- `IMPACTLENS_DATABASE`: SQLite path.
- `IMPACTLENS_EMBEDDING_MODEL`: embedding model label.
- `IMPACTLENS_LLM_PROVIDER`: provider label.
- `GITHUB_TOKEN`: optional GitHub API token.
- `GITHUB_WEBHOOK_SECRET`: required HMAC signing secret.

Never commit credentials.

## Testing

```bash
pytest -q
```

## Docker

```bash
docker build -t impactlens .
docker run --rm -p 8000:8000 impactlens
```

## Known limitations

- Static analysis misses runtime-generated dependencies.
- Offline embeddings are deterministic hash vectors, not transformer embeddings.
- The RAG provider is offline and template-based; no hosted LLM is required or claimed.
- Chroma is declared in dependencies but the current retrieval implementation is SQLite + in-memory dense/BM25 ranking.
- No valid labelled dataset exists, so ML risk prediction is not available.
- GitHub publishing is not implemented; webhook signature verification is implemented.
- Synthetic demo data is not evidence of real-world performance.