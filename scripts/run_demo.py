import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import initialize_database
from app.ingestion.repository_loader import ingest_repository
from app.retrieval.hybrid_retriever import retrieve


def main() -> None:
    initialize_database()
    repository_id = "demo"
    from app.database.connection import database
    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES (?, ?, NULL, '0', 'registered', '2026-01-01')",
            (repository_id, "data/sample_repository"),
        )
        connection.commit()
    print(ingest_repository(repository_id, "data/sample_repository"))
    print(retrieve(repository_id, "payment tax calculation", limit=5))


if __name__ == "__main__":
    main()
