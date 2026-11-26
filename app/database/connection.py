import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import DATABASE_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL UNIQUE,
    local_path TEXT,
    remote_url TEXT,
    index_version TEXT NOT NULL DEFAULT '0',
    status TEXT NOT NULL DEFAULT 'registered',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_documents (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    file_path TEXT,
    content_hash TEXT NOT NULL,
    document_version INTEGER NOT NULL DEFAULT 1,
    deleted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    UNIQUE(repository_id, source_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    chunk_id TEXT NOT NULL UNIQUE,
    repository_id TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    file_path TEXT,
    symbol_name TEXT,
    commit_sha TEXT,
    created_at TEXT,
    content_hash TEXT NOT NULL,
    document_version INTEGER NOT NULL DEFAULT 1,
    embedding_model TEXT NOT NULL,
    access_scope TEXT NOT NULL DEFAULT 'repository',
    content TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES source_documents(id)
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL,
    stable_id TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    evidence_source TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    evidence_strength TEXT NOT NULL DEFAULT 'static',
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL,
    status TEXT NOT NULL,
    files_seen INTEGER NOT NULL DEFAULT 0,
    chunks_written INTEGER NOT NULL DEFAULT 0,
    files_deleted INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY,
    repository_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    reference TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_repository ON chunks(repository_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(repository_id, source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(repository_id, target_id);
"""


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)


@contextmanager
def database():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()
