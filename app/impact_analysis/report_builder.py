from app.retrieval.hybrid_retriever import retrieve
from app.graph.traversal import neighbors


def build_impact_report(repository_id: str, question: str, limit: int = 10) -> dict:
    evidence = retrieve(repository_id, question, limit=limit)
    graph_evidence = []
    for item in evidence:
        if item["symbol_name"]:
            graph_evidence.extend(neighbors(repository_id, item["symbol_name"], max_depth=2, limit=8))
    return {
        "repository_id": repository_id,
        "summary": (
            "Potential impact is based only on retrieved repository evidence and statically "
            "detected relationships; it is not a runtime guarantee."
        ),
        "evidence": evidence,
        "relationship_evidence": graph_evidence,
        "tests": [
            item["file_path"] for item in evidence
            if item["source_type"] == "python" and "/test" in item["file_path"].lower()
        ],
        "uncertainties": [
            "Dynamic dispatch, reflection, dependency injection, monkey patching, and external calls may not be visible.",
            "Retrieval relevance and historical similarity do not prove root cause.",
        ],
    }
