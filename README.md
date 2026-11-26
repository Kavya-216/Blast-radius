# ImpactLens

**Understand the evidence around a code change before it reaches production.**

ImpactLens is a decision-support prototype for exploring software repositories. It retrieves source code and engineering documents, extracts some Python relationships, and presents evidence for repository questions, PR reviews, and incident investigations. It does not prove that a change is safe or identify every dependency.

## What you can do

### Ask the repository

Ask questions about source, tests, architecture notes, or incident records. Connect a public GitHub repository from the sidebar without cloning it. For each query, ImpactLens reads the GitHub file tree, fetches a bounded set of relevant text files, ranks their chunks, and displays the supporting paths.

The response includes a short **plain-English paragraph** grounded in retrieved files, followed by expandable source evidence. It uses deterministic summaries, not a hosted LLM or free-form generated explanation. If retrieval finds no evidence, it says so rather than inventing an answer.

### Analyze a PR

Enter a PR number, title, and description. For a connected GitHub repository, ImpactLens fetches the PR diff read-only, uses changed paths and patch lines to retrieve related code and tests, and includes a bounded diff excerpt as evidence. Local repositories continue to use the supplied title and description.

Diff downloads are capped at 1 MB; displayed diff evidence and changed-line retrieval context are capped at 20,000 and 10,000 characters, respectively. The risk-model panel reports that no trained model is available; it does not produce a risk score.

### Investigate an incident

Enter an incident description or stack trace. ImpactLens retrieves related source and demo incident records, presents possible explanations as hypotheses, and suggests investigation steps. Similarity is not proof of root cause.

### Index a local repository

The demo button indexes the local `data/` fixtures. The API also supports registering and indexing a local path. Ingestion hashes files, skips unchanged content, chunks supported formats, and extracts Python symbols and static relationships.

## How it works

```text
Local repository or GitHub file tree
            |
            v
Source-aware chunks + Python AST extraction
            |
            v
SQLite metadata and relationship records
            |
            v
BM25 + deterministic hash-vector ranking
            |
            v
Reciprocal Rank Fusion -> evidence summary and citations
```

For remote GitHub queries, the app requests repository metadata and a recursive file tree, then fetches at most 12 candidate text files (each at most 250 KB) per question. It does not clone or persist those remote files. GitHub API limits, large truncated trees, and path-based candidate selection can reduce coverage.

## Quick start

Python 3.12 or newer is recommended.

```bash
python -m pip install -r requirements.txt
```

Run the API and UI in separate terminals from the project root:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
streamlit run frontend/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Open the UI at `http://localhost:8501` and the API docs at `http://localhost:8000/docs`.

### Try the local demo

In the UI sidebar, click **Index demo repository**. The synthetic source, architecture, and incident fixtures are in `data/`.

### Connect a GitHub repository without cloning

In the sidebar, paste a GitHub URL such as:

```text
https://github.com/HKUDS/RAG-Anything.git
```

Click **Connect without cloning**. The selected repository ID will update automatically. Then choose **Ask the repository** and ask a question in the main panel. Private repositories need a configured `GITHUB_TOKEN`; only GitHub-hosted URLs are accepted.

### API example

```bash
curl -X POST http://localhost:8000/repositories/connect-github \
  -H 'Content-Type: application/json' \
  -d '{"remote_url":"https://github.com/HKUDS/RAG-Anything.git"}'
```

Use the returned `repository_id` to query:

```bash
curl -X POST http://localhost:8000/rag/query \
  -H 'Content-Type: application/json' \
  -d '{"repository_id":"github-hkuds-rag-anything","question":"How does the RAG pipeline work?"}'
```

## Technology

- Python, FastAPI, Pydantic, Uvicorn, Streamlit
- SQLite for local metadata, chunks, symbols, and relationships
- Python `ast` for static source analysis
- Built-in `urllib` for GitHub API and raw-file requests
- BM25, deterministic 128-dimensional hash vectors, cosine similarity, and RRF
- Pytest and HTTPX

The dependency list contains only packages used by the current app and tests. No Chroma vector store, hosted LLM, transformer embedding model, reranker, trained ML model, or MLflow experiment is active.

## API routes

- `GET /health`
- `POST /repositories` — register a local repository
- `GET /repositories/{id}`
- `POST /repositories/{id}/index`
- `GET /repositories/{id}/retrieve?query=...`
- `POST /repositories/connect-github` — connect a GitHub repository without cloning
- `POST /rag/query`
- `POST /prs/analyze`
- `POST /incidents/investigate`
- `POST /webhooks/github` — verify a configured webhook signature and acknowledge the event

FastAPI’s interactive documentation is available at `/docs`.

## Configuration

Set environment variables as needed:

- `IMPACTLENS_DATABASE` — SQLite database path
- `IMPACTLENS_EMBEDDING_MODEL` — displayed embedding label; current vectors are deterministic hashes
- `IMPACTLENS_LLM_PROVIDER` — displayed provider label; current generation is offline
- `GITHUB_TOKEN` — optional token for GitHub API requests and private repository access
- `GITHUB_WEBHOOK_SECRET` — required to accept signed GitHub webhooks

Never commit credentials.

## Development and evaluation

```bash
pytest -q
python scripts/run_demo.py
python scripts/run_evaluation.py
```

The evaluation script is a smoke test, not a retrieval benchmark. No relevance-labelled dataset or ML training data is included, so no retrieval-quality or risk-model metrics are claimed.

## What is and is not implemented

| Area | Current status |
|---|---|
| Local file discovery, content hashes, chunking, SQLite persistence | Implemented |
| Python symbols, imports, and statically detected calls | Implemented; incomplete by nature |
| Dense-style hash-vector retrieval, BM25, RRF | Implemented; not benchmarked |
| Graph relationship storage and bounded traversal | Implemented |
| GitHub no-clone retrieval | Implemented for bounded text-file fetching |
| Repository Q&A | Implemented as evidence formatting with citation checks and abstention |
| PR impact UI | Read-only live diff for connected GitHub repositories; manual metadata for local repositories |
| Incident investigation | Similarity-based evidence and explicitly labelled hypotheses |
| Webhook signature verification | Implemented; no automatic PR processing |
| GitHub Check Runs/comments and webhook event processing | Not implemented |
| Trained regression-risk model | Not available without labelled training data |
| Chroma vector storage, hosted LLM, reranking, MLflow | Not active |

## Limitations

- Python dynamic imports, reflection, dispatch, dependency injection, and runtime behavior are not fully visible to AST analysis.
- Hash embeddings are deterministic lexical features, not semantic transformer embeddings.
- Remote retrieval selects files partly by their paths; relevant files can be missed.
- GitHub rate limits and recursive-tree truncation can limit remote queries.
- The offline summary uses deterministic sentence selection and can summarize explicit layer-size tables for architecture questions; it does not perform free-form LLM synthesis or guarantee a complete explanation. Documentation cross-reference and code lines are not treated as summary prose.
- Synthetic incidents and sample repositories are demo data, not real engineering history.
- No benchmark establishes production accuracy or safety.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md), [docs/SECURITY.md](docs/SECURITY.md), and [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for additional detail.
