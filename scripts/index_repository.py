import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import initialize_database
from app.ingestion.repository_loader import ingest_repository


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/index_repository.py <repository-id> <path>")
    initialize_database()
    print(ingest_repository(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
