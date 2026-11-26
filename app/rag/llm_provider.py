from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    citations: list[str]


def generate_answer(question: str, evidence: list[dict]) -> GenerationResult:
    if not evidence:
        return GenerationResult(
            text="Insufficient evidence was retrieved to answer this question.",
            provider="offline-deterministic",
            citations=[],
        )
    lines = [f"Evidence-based answer for: {question.strip()}"]
    citations = []
    for item in evidence[:5]:
        citation = f"{item['source_type']}:{item['file_path']}"
        citations.append(citation)
        excerpt = " ".join(item["content"].split())[:300]
        lines.append(f"- [{citation}] {excerpt}")
    lines.append("This response is assembled from retrieved repository evidence, not a hosted LLM.")
    return GenerationResult(
        text="\n".join(lines),
        provider="offline-deterministic",
        citations=citations,
    )
