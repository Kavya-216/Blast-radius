from datetime import datetime, timezone
from pathlib import Path
import hashlib

from app.database.connection import database


def discover_files(root: Path) -> list[Path]:
    excluded = {".git", ".venv", "__pycache__", "node_modules", "chroma"}
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and not any(part in excluded for part in path.parts)
        and path.suffix.lower() in {".py", ".md", ".txt", ".json"}
    )


def ingest_repository(repository_id: str, local_path: str) -> dict:
    root = Path(local_path).resolve()
    if not root.is_dir():
        return {"status": "failed", "error": "local_path is not a directory", "chunks": 0}

    files = discover_files(root)
    now = datetime.now(timezone.utc).isoformat()
    chunks_written = 0
    seen_paths: set[str] = set()

    from app.ingestion.chunking import chunk_markdown, chunk_plaintext, chunk_python

    with database() as connection:
        job = connection.execute(
            "INSERT INTO ingestion_jobs "
            "(repository_id, status, files_seen, chunks_written, started_at) "
            "VALUES (?, 'running', 0, 0, ?)",
            (repository_id, now),
        )
        job_id = job.lastrowid
        try:
            for path in files:
                relative = path.relative_to(root).as_posix()
                seen_paths.add(relative)
                content = path.read_text(encoding="utf-8", errors="replace")
                digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

                existing = connection.execute(
                    "SELECT id, content_hash, document_version FROM source_documents "
                    "WHERE repository_id=? AND source_id=?",
                    (repository_id, relative),
                ).fetchone()
                if existing and existing["content_hash"] == digest:
                    continue

                if existing:
                    document_version = existing["document_version"] + 1
                    document_id = existing["id"]
                    connection.execute(
                        "UPDATE source_documents SET content_hash=?, document_version=?, "
                        "deleted=0, updated_at=? WHERE id=?",
                        (digest, document_version, now, document_id),
                    )
                else:
                    source_type = "python" if path.suffix == ".py" else (
                        "markdown" if path.suffix == ".md" else "text"
                    )
                    cursor = connection.execute(
                        "INSERT INTO source_documents "
                        "(repository_id, source_type, source_id, file_path, content_hash, "
                        "document_version, deleted, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, 1, 0, ?)",
                        (repository_id, source_type, relative, relative, digest, now),
                    )
                    document_id = cursor.lastrowid
                    document_version = 1

                connection.execute(
                    "DELETE FROM chunks WHERE repository_id=? AND source_id=?",
                    (repository_id, relative),
                )
                if path.suffix == ".py":
                    chunks = chunk_python(content, relative)
                elif path.suffix == ".md":
                    chunks = chunk_markdown(content, relative)
                else:
                    chunks = chunk_plaintext(content, relative)

                for chunk in chunks:
                    connection.execute(
                        "INSERT INTO chunks "
                        "(chunk_id, repository_id, document_id, source_type, source_id, "
                        "file_path, symbol_name, content_hash, document_version, "
                        "embedding_model, access_scope, content) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'offline-hash-v1', "
                        "'repository', ?)",
                        (
                            f"{repository_id}:{chunk.chunk_id}",
                            repository_id,
                            document_id,
                            chunk.source_type,
                            chunk.source_id,
                            chunk.file_path,
                            chunk.symbol_name,
                            chunk.content_hash,
                            document_version,
                            chunk.content,
                        ),
                    )
                    chunks_written += 1

                if path.suffix == ".py":
                    from app.code_analysis.ast_parser import analyze_python_file
                    from app.graph.graph_store import store_symbols_and_relationships
                    symbols, relationships = analyze_python_file(repository_id, relative, content)
                    store_symbols_and_relationships(repository_id, symbols, relationships, connection)

            stale = connection.execute(
                "SELECT source_id, id FROM source_documents "
                "WHERE repository_id=? AND deleted=0",
                (repository_id,),
            ).fetchall()
            deleted = 0
            for row in stale:
                if row["source_id"] not in seen_paths:
                    connection.execute(
                        "UPDATE source_documents SET deleted=1, updated_at=? WHERE id=?",
                        (now, row["id"]),
                    )
                    connection.execute(
                        "DELETE FROM chunks WHERE repository_id=? AND source_id=?",
                        (repository_id, row["source_id"]),
                    )
                    deleted += 1

            connection.execute(
                "UPDATE repositories SET status='indexed', index_version=index_version+1, "
                "updated_at=? WHERE repository_id=?",
                (now, repository_id),
            )
            connection.execute(
                "UPDATE ingestion_jobs SET status='completed', files_seen=?, "
                "chunks_written=?, files_deleted=?, finished_at=? WHERE id=?",
                (len(files), chunks_written, deleted, now, job_id),
            )
            connection.commit()
        except Exception as exc:
            connection.execute(
                "UPDATE ingestion_jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                (str(exc), now, job_id),
            )
            connection.execute(
                "UPDATE repositories SET status='failed', updated_at=? WHERE repository_id=?",
                (now, repository_id),
            )
            connection.commit()
            return {"status": "failed", "error": str(exc), "chunks": 0}
    return {
        "status": "completed",
        "files_seen": len(files),
        "chunks_written": chunks_written,
        "files_deleted": deleted,
    }
