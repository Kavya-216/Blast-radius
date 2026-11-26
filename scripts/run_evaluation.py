import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import initialize_database, database
from app.ingestion.repository_loader import ingest_repository
from app.retrieval.hybrid_retriever import retrieve


def main() -> None:
    initialize_database()
    repository_id = "evaluation-demo"
    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES (?, 'data/sample_repository', NULL, '0', 'registered', '2026-01-01')",
            (repository_id,),
        )
        connection.commit()
    indexing = ingest_repository(repository_id, "data/sample_repository")
    retrieval = retrieve(repository_id, "payment tax test", limit=5)
    print({"indexing": indexing, "retrieved": len(retrieval), "top_file": retrieval[0]["file_path"] if retrieval else None})
    print("No gold relevance labels are configured; retrieval metrics are not claimed.")


if __name__ == "__main__":
    main()
