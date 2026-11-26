from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import initialize_database, database
from app.ingestion.repository_loader import ingest_repository


client = TestClient(app)


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
