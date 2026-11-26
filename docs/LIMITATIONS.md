# Limitations

- Static Python AST analysis cannot infer reflection, dynamic imports, dependency injection, monkey patching, runtime registration, or generated code.
- Hash embeddings provide lexical/deterministic similarity only.
- The offline RAG provider is a deterministic evidence formatter, not a generative LLM.
- No hosting, reranker, Chroma integration, or MLflow experiment is active.
- GitHub publishing is not implemented.
- Historical and incident evidence is sparse in the demo dataset.
- No retrieval gold set or production benchmark is available.
- The PR diff endpoint payload is intentionally local/demo-oriented.
