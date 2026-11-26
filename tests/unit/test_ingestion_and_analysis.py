from pathlib import Path

from app.ingestion.repository_loader import ingest_repository
from app.database.connection import initialize_database, database
from app.code_analysis.ast_parser import analyze_python_file
from app.retrieval.bm25 import BM25
from app.retrieval.rrf import reciprocal_rank_fusion
from app.github.webhook import verify_github_signature
from app.ingestion.chunking import chunk_markdown, chunk_python
import hashlib
import hmac


def test_ast_extracts_class_function_import_and_call():
    content = "import math\n\nclass Example:\n    def run(self):\n        return math.sqrt(4)\n"
    symbols, relationships = analyze_python_file("repo", "src/example.py", content)
    names = {symbol.qualified_name for symbol in symbols}
    assert "src.example.Example" in names
    assert "src.example.run" in names
    assert any(item.relationship_type == "IMPORTS" for item in relationships)
    assert any(item.relationship_type == "CALLS" for item in relationships)


def test_bm25_returns_relevant_document():
    bm25 = BM25().fit([
        "payment tax calculation",
        "authentication login flow",
    ])
    hits = bm25.search("tax")
    assert hits
    assert hits[0][0] == 0


def test_rrf_deduplicates_results():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    ids = [item[0] for item in fused]
    assert ids.count("b") == 1
    assert set(ids) == {"a", "b", "c"}


def test_incremental_ingestion(tmp_path):
    initialize_database()
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "main.py").write_text("def main():\n    return 1\n")

    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES (?, ?, NULL, '0', 'registered', '2026-01-01')",
            ("test-repo", str(repo)),
        )
        connection.commit()

    first = ingest_repository("test-repo", str(repo))
    second = ingest_repository("test-repo", str(repo))
    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert second["chunks_written"] == 0


def test_github_webhook_signature_verification():
    body = b'{"zen":"test"}'
    secret = "demo-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(secret, body, f"sha256={digest}")
    assert not verify_github_signature(secret, body, "sha256=wrong")


def test_source_chunks_have_unique_ids_for_repeated_names_and_headings():
    python_chunks = chunk_python(
        "class First:\n    def run(self):\n        pass\n"
        "class Second:\n    def run(self):\n        pass\n",
        "src/example.py",
    )
    markdown_chunks = chunk_markdown(
        "# Overview\nFirst section.\n# Overview\nSecond section.\n",
        "README.md",
    )
    assert len({chunk.chunk_id for chunk in python_chunks}) == len(python_chunks)
    assert len({chunk.chunk_id for chunk in markdown_chunks}) == len(markdown_chunks)
