from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import initialize_database, database
from app.ingestion.repository_loader import ingest_repository
from app.github.repository_url import parse_public_github_url


client = TestClient(app)


def test_github_import_accepts_only_public_github_urls():
    repo_id, owner, repository = parse_public_github_url(
        "https://github.com/HKUDS/RAG-Anything.git"
    )
    assert repo_id == "github-hkuds-rag-anything"
    assert (owner, repository) == ("HKUDS", "RAG-Anything")

    for url in (
        "http://github.com/HKUDS/RAG-Anything",
        "https://example.com/HKUDS/RAG-Anything",
        "https://github.com/HKUDS/RAG-Anything/tree/main",
        "https://user:pass@github.com/HKUDS/RAG-Anything",
    ):
        try:
            parse_public_github_url(url)
        except ValueError:
            continue
        raise AssertionError(f"Unexpectedly accepted URL: {url}")


def test_github_import_endpoint_rejects_non_github_url():
    response = client.post(
        "/repositories/connect-github",
        json={"remote_url": "https://example.com/owner/repo"},
    )
    assert response.status_code == 422


def test_github_connection_does_not_clone_repository():
    response = client.post(
        "/repositories/connect-github",
        json={"remote_url": "https://github.com/HKUDS/RAG-Anything.git"},
    )
    assert response.status_code == 200
    repo_id = response.json()["repository_id"]
    with database() as connection:
        row = connection.execute(
            "SELECT local_path, remote_url FROM repositories WHERE repository_id=?",
            (repo_id,),
        ).fetchone()
    assert row["local_path"] is None
    assert row["remote_url"].endswith("RAG-Anything.git")


def test_remote_github_query_fetches_relevant_files_on_demand(monkeypatch):
    import json
    from app.retrieval import github_retriever

    def fake_github_request(url, accept):
        if url.endswith("/repos/HKUDS/RAG-Anything"):
            return json.dumps({"default_branch": "main"}).encode()
        if "/git/trees/" in url:
            return json.dumps({
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 80},
                    {"path": "src/pipeline.py", "type": "blob", "size": 80},
                ],
            }).encode()
        if url.endswith("/README.md"):
            return b"# Architecture\nRAG pipeline retrieves documents and builds context."
        if url.endswith("/src/pipeline.py"):
            return b"def retrieve_documents(query):\n    return query\n"
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(github_retriever, "_github_request", fake_github_request)
    client.post(
        "/repositories/connect-github",
        json={"remote_url": "https://github.com/HKUDS/RAG-Anything.git"},
    )
    response = client.post("/rag/query", json={
        "repository_id": "github-hkuds-rag-anything",
        "question": "How does the RAG pipeline retrieve documents?",
    })
    assert response.status_code == 200
    assert response.json()["abstained"] is False
    assert any("README.md" in item["file_path"] for item in response.json()["evidence"])
    assert response.json()["citation_validation"]["supported"] is True


def test_rag_abstains_for_empty_repository(tmp_path):
    initialize_database()
    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES ('empty-workflow', ?, NULL, '0', 'registered', '2026-01-01')",
            (str(tmp_path),),
        )
        connection.commit()
    response = client.post("/rag/query", json={
        "repository_id": "empty-workflow",
        "question": "How does authentication work?",
    })
    assert response.status_code == 200
    assert response.json()["abstained"] is True


def test_pr_and_incident_workflows_with_demo_index():
    initialize_database()
    rid = "workflow-demo"
    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES (?, 'data/sample_repository', NULL, '0', 'registered', '2026-01-01')",
            (rid,),
        )
        connection.commit()
    ingest_repository(rid, "data/sample_repository")
    pr = client.post("/prs/analyze", json={
        "repository_id": rid,
        "pull_request_number": "1",
        "title": "Payment tax update",
        "description": "Change payment tax calculation.",
    })
    assert pr.status_code == 200
    assert pr.json()["risk"]["status"] == "not_available"

    incident = client.post("/incidents/investigate", json={
        "repository_id": rid,
        "description": "Payment totals are incorrect",
    })
    assert incident.status_code == 200
    assert "status" in incident.json()


def test_demo_architecture_document_is_retrievable():
    initialize_database()
    rid = "architecture-demo"
    with database() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO repositories "
            "(repository_id, local_path, remote_url, index_version, status, updated_at) "
            "VALUES (?, 'data', NULL, '0', 'registered', '2026-01-01')",
            (rid,),
        )
        connection.commit()
    ingest_repository(rid, "data")
    response = client.get(
        f"/repositories/{rid}/retrieve",
        params={"query": "architecture payment billing", "limit": 10},
    )
    assert response.status_code == 200
    paths = [item["file_path"] for item in response.json()["results"]]
    assert any("architecture" in path for path in paths)
