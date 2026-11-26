# Limitations

- Static Python AST analysis cannot infer reflection, dynamic imports, dependency injection, monkey patching, runtime registration, or generated code.
- Hash embeddings provide lexical/deterministic similarity only.
- The offline RAG provider is a deterministic evidence formatter, not a generative LLM.
- No hosting, reranker, Chroma integration, or MLflow experiment is active.
- GitHub publishing is not implemented.
- Connected GitHub repositories support read-only PR diff retrieval. Diffs are limited to 1 MB; the report displays at most 20,000 characters and uses at most 10,000 changed-line characters as retrieval context. Local repositories still rely on entered PR metadata.
- Remote retrieval reads GitHub's file tree and fetches a bounded set of text files per query; it does not clone the repository. Large/truncated GitHub trees and API rate limits can limit retrieval. Public GitHub repositories are supported; private repositories require a configured token.
- Historical and incident evidence is sparse in the demo dataset.
- No retrieval gold set or production benchmark is available.
