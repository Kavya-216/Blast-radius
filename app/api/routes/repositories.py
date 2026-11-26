from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.schemas.common import RepositoryRegistration, RepositoryStatus
from app.database.connection import database
from app.ingestion.repository_loader import ingest_repository
from app.retrieval.hybrid_retriever import retrieve


router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryStatus, status_code=201)
def register_repository(payload: RepositoryRegistration) -> RepositoryStatus:
    now = datetime.now(timezone.utc).isoformat()
    with database() as connection:
        connection.execute(
            """
            INSERT INTO repositories
                (repository_id, local_path, remote_url, index_version, status, updated_at)
            VALUES (?, ?, ?, '0', 'registered', ?)
            ON CONFLICT(repository_id) DO UPDATE SET
                local_path=excluded.local_path,
                remote_url=excluded.remote_url,
                updated_at=excluded.updated_at
            """,
            (payload.repository_id, payload.local_path, payload.remote_url, now),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM repositories WHERE repository_id = ?",
            (payload.repository_id,),
        ).fetchone()
    return RepositoryStatus(
        repository_id=row["repository_id"],
        local_path=row["local_path"],
        remote_url=row["remote_url"],
        index_version=row["index_version"],
        status=row["status"],
    )


@router.get("/{repository_id}", response_model=RepositoryStatus)
def get_repository(repository_id: str) -> RepositoryStatus:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM repositories WHERE repository_id = ?",
            (repository_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryStatus(
        repository_id=row["repository_id"],
        local_path=row["local_path"],
        remote_url=row["remote_url"],
        index_version=row["index_version"],
        status=row["status"],
    )


@router.post("/{repository_id}/index")
def index_repository(repository_id: str) -> dict:
    with database() as connection:
        row = connection.execute(
            "SELECT local_path FROM repositories WHERE repository_id=?",
            (repository_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return ingest_repository(repository_id, row["local_path"])


@router.get("/{repository_id}/retrieve")
def retrieve_repository(repository_id: str, query: str, limit: int = 10) -> dict:
    if not query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")
    return {
        "repository_id": repository_id,
        "query": query,
        "results": retrieve(repository_id, query, limit=min(limit, 50)),
    }
