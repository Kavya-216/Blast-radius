# Evaluation

The repository includes unit and integration tests for AST extraction, BM25, RRF, incremental ingestion, webhook verification, RAG abstention, PR reports, and incident investigation.

Run:

```bash
pytest -q
python scripts/run_evaluation.py
```

The benchmark script must not report synthetic results as real-world production performance. No retrieval or ML metrics have been fabricated. Retrieval quality depends on an externally supplied gold set.
