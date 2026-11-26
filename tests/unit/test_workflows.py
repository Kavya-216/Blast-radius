import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import initialize_database, database
from app.ingestion.repository_loader import ingest_repository
from app.github.repository_url import parse_public_github_url
from app.rag.llm_provider import generate_answer
from app.rag.citation_validator import validate_citations


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


def test_rag_answer_is_a_cited_plain_english_paragraph():
    evidence = [{
        "source_type": "markdown",
        "file_path": "docs/retrieval.md",
        "content": (
            "The retrieval pipeline first finds useful document passages using keyword matching. "
            "It combines those results with vector similarity to improve coverage."
        ),
    }]
    result = generate_answer("How does the retrieval pipeline work?", evidence)
    assert result.text.startswith("In simple terms, ")
    assert "\n" not in result.text
    assert result.citations == ["markdown:docs/retrieval.md"]
    assert validate_citations(result.text, evidence)["supported"] is True


def test_architecture_summary_uses_only_repo_specific_evidence():
    evidence = [
        {
            "source_type": "markdown",
            "file_path": "docs/snn.md",
            "symbol_name": "Component 1: SNN Architecture",
            "content": (
                "The network has two spiking hidden layers with 128 and 64 neurons. "
                "Its output layer has three neurons for classification."
            ),
        },
        {
            "source_type": "markdown",
            "file_path": "docs/snn.md",
            "symbol_name": "Training",
            "content": "Adam updates the weights using surrogate gradients.",
        },
    ]
    result = generate_answer("Explain the architecture", evidence)
    assert "two spiking hidden layers" in result.text
    assert "RAG-Anything" not in result.text
    assert "multimodal knowledge graph" not in result.text
    assert validate_citations(result.text, evidence)["supported"] is True


def test_architecture_retrieval_prioritizes_generic_structure_sections():
    from app.retrieval.github_retriever import _intent_ranking

    chunks = [
        {"chunk_id": "overview", "symbol_name": "Architecture Overview"},
        {"chunk_id": "network", "symbol_name": "Network Structure"},
        {"chunk_id": "layers", "symbol_name": "Layer Design Rationale"},
        {"chunk_id": "other", "symbol_name": "Incident Response"},
    ]
    assert _intent_ranking(chunks, "Explain the model architecture") == [
        "network",
        "layers",
        "overview",
    ]


def test_summary_ignores_claims_in_document_cross_reference():
    evidence = [
        {
            "source_type": "markdown",
            "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
            "symbol_name": "Model Architecture Details",
            "content": (
                "See [Component 1: Model Architecture](./ARCH_4_SNN_TRAINING.md)"
                " (lines 15-35): The input layer has 64 LIF neurons, the hidden layer "
                "has 128 LIF neurons, and the output layer has 3 non-spiking neurons."
            ),
        },
        {
            "source_type": "markdown",
            "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
            "symbol_name": "Component 1: SNN Architecture",
            "content": (
                "The network has two spiking hidden layers with 128 and 64 neurons. "
                "Its output layer has three neurons for classification."
            ),
        },
    ]
    result = generate_answer("Explain the architecture", evidence)
    assert "two spiking hidden layers" in result.text
    assert "input layer has 64 LIF neurons" not in result.text
    assert "See Component 1" not in result.text
    assert "lines 15-35" not in result.text
    assert validate_citations(result.text, evidence)["supported"] is True


def test_summary_abstains_when_evidence_is_only_a_cross_reference():
    evidence = [{
        "source_type": "markdown",
        "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
        "symbol_name": "Model Architecture Details",
        "content": (
            "See Component 1: Model Architecture (lines 15-35): The input layer "
            "has 64 LIF neurons and a 128-neuron hidden layer."
        ),
    }]
    result = generate_answer("Explain the architecture", evidence)
    assert "not enough explanatory prose" in result.text
    assert result.citations == []


def test_summary_skips_code_exposed_by_markdown_chunking():
    evidence = [
        {
            "source_type": "markdown",
            "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
            "content": "model = load_checkpoint('model_checkpoint.pth')",
        },
        {
            "source_type": "markdown",
            "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
            "content": (
                "- **Hidden Layer**: 128 LIF neurons with weight matrix W1 (64x128). "
                "- **Output Layer**: 3 output neurons (dense, non-spiking) for classification."
            ),
        },
    ]
    result = generate_answer("Explain the model architecture in simple terms", evidence)
    assert "load_checkpoint" not in result.text
    assert "128 LIF neurons" in result.text
    assert validate_citations(result.text, evidence)["supported"] is True


def test_architecture_summary_uses_layer_dimensions_from_markdown_table():
    evidence = [{
        "source_type": "markdown",
        "file_path": "docs/architecture/ARCH_4_SNN_TRAINING.md",
        "content": (
            "| Layer | Input Size | Output Size | Type | Rationale |\n"
            "|---|---:|---:|---|---|\n"
            "| Hidden 1 | 64 | 128 | Spiking LIF | Feature extraction |\n"
            "| Hidden 2 | 128 | 64 | Spiking LIF | Dimensionality reduction |\n"
            "| Output | 64 | 3 | Non-spiking | Classification |\n"
        ),
    }]
    result = generate_answer("Explain the architecture", evidence)
    assert "64 inputs" in result.text
    assert "128 and 64 neurons" in result.text
    assert "3 outputs" in result.text
    assert validate_citations(result.text, evidence)["supported"] is True


def test_github_import_endpoint_rejects_non_github_url():
    response = client.post(
        "/repositories/connect-github",
        json={"remote_url": "https://example.com/owner/repo"},
    )
    assert response.status_code == 422


def test_pull_request_diff_fetch_parses_paths_and_line_counts(monkeypatch):
    from app.github import pull_requests

    diff = (
        "diff --git a/src/payments.py b/src/payments.py\n"
        "--- a/src/payments.py\n"
        "+++ b/src/payments.py\n"
        "@@ -1 +1 @@\n"
        "-def old_tax():\n"
        "+def calculate_tax():\n"
        "diff --git a/tests/test_payments.py b/tests/test_payments.py\n"
        "--- /dev/null\n"
        "+++ b/tests/test_payments.py\n"
        "@@ -0,0 +1 @@\n"
        "+def test_calculate_tax():\n"
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size):
            assert size == pull_requests.MAX_PULL_REQUEST_DIFF_BYTES + 1
            return diff.encode()

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/pulls/7")
        assert request.get_header("Accept") == "application/vnd.github.diff"
        assert timeout == 20
        return FakeResponse()

    monkeypatch.setattr(pull_requests, "urlopen", fake_urlopen)
    result = pull_requests.fetch_pull_request_diff(
        "https://github.com/acme/payments.git", 7
    )
    assert result["changed_files"] == [
        "src/payments.py",
        "tests/test_payments.py",
    ]
    assert result["additions"] == 2
    assert result["deletions"] == 1
    assert "calculate_tax" in result["change_context"]
    assert result["change_context_truncated"] is False


def test_pull_request_diff_fetch_rejects_oversized_diff(monkeypatch):
    from app.github import pull_requests

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size):
            return b"x" * size

    monkeypatch.setattr(
        pull_requests,
        "urlopen",
        lambda request, timeout: FakeResponse(),
    )
    with pytest.raises(RuntimeError, match="1 MB analysis limit"):
        pull_requests.fetch_pull_request_diff(
            "https://github.com/acme/payments.git", 7
        )


def test_remote_pr_analysis_uses_live_diff_as_evidence(monkeypatch):
    from app.api.routes import workflows

    connected = client.post(
        "/repositories/connect-github",
        json={"remote_url": "https://github.com/acme/pr-analysis.git"},
    )
    repository_id = connected.json()["repository_id"]
    monkeypatch.setattr(
        workflows,
        "fetch_pull_request_diff",
        lambda remote_url, number: {
            "changed_files": ["src/payments.py", "tests/test_payments.py"],
            "additions": 2,
            "deletions": 1,
            "diff": "diff content",
            "diff_excerpt": "diff --git a/src/payments.py b/src/payments.py",
            "diff_truncated": False,
            "change_context": "+def calculate_tax():",
            "change_context_truncated": False,
        },
    )
    query = {}

    def fake_retrieve(rid, question, limit):
        query["text"] = question
        return []

    monkeypatch.setattr("app.impact_analysis.report_builder.retrieve", fake_retrieve)
    response = client.post("/prs/analyze", json={
        "repository_id": repository_id,
        "pull_request_number": "7",
        "title": "Update payment tax",
        "description": "Use a new tax calculation.",
    })

    assert response.status_code == 200
    result = response.json()
    assert result["pull_request"]["changed_files"] == [
        "src/payments.py",
        "tests/test_payments.py",
    ]
    assert result["tests"] == ["tests/test_payments.py"]
    assert result["evidence"][0]["source_type"] == "diff"
    assert "src/payments.py" in query["text"]
    assert "calculate_tax" in query["text"]


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
    assert "pipeline retrieves documents" in response.json()["answer"]
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
