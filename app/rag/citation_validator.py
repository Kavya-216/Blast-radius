def validate_citations(answer: str, evidence: list[dict]) -> dict:
    valid = {
        f"{item['source_type']}:{item['file_path']}"
        for item in evidence
    }
    cited = {
        token.strip("[]")
        for token in answer.split()
        if token.startswith("[") and ":" in token
    }
    unsupported = sorted(cited - valid)
    return {
        "supported": not unsupported,
        "unsupported_citations": unsupported,
        "evidence_count": len(evidence),
    }
