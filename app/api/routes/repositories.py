from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.schemas.common import RepositoryRegistration, RepositoryStatus
from app.database.connection import database


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
