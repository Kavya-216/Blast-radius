from app.retrieval.hybrid_retriever import retrieve


def investigate(repository_id: str, description: str, limit: int = 10) -> dict:
    evidence = retrieve(repository_id, description, limit=limit)
    incidents = [item for item in evidence if "incident" in item["file_path"].lower()]
    if not evidence:
        return {
            "status": "insufficient_evidence",
            "hypotheses": [],
            "historical_incidents": [],
            "evidence": [],
            "suggested_steps": ["Confirm affected module and collect a stack trace."],
        }
    return {
        "status": "evidence_retrieved",
        "historical_incidents": incidents,
        "related_components": sorted({
            item["symbol_name"] for item in evidence if item["symbol_name"]
        }),
        "evidence": evidence,
        "hypotheses": [
            "Similarity is a lead for investigation, not a demonstrated root cause."
        ],
        "suggested_steps": [
            "Reproduce the issue in an isolated test.",
            "Verify the affected module and its statically detected dependencies.",
            "Review the cited evidence and recent changes.",
        ],
    }
