from dataclasses import dataclass
import re

from app.retrieval.bm25 import BM25


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
    sentences: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in evidence:
        if item["source_type"] not in {"markdown", "text"}:
            continue
        in_code_block = False
        for raw_line in item["content"].splitlines():
            line = raw_line.strip()
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line or line.startswith("#") or line.startswith("|"):
                continue
            line = re.sub(r"^[-*]\s+", "", line)
            line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
            line = re.sub(r"`([^`]*)`", r"\1", line)
            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            citation = f"{item['source_type']}:{item['file_path']}"
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                sentence = sentence.strip()
                if 45 <= len(sentence) <= 360 and sentence not in seen:
                    sentences.append((sentence, citation))
                    seen.add(sentence)

    ranked = []
    if sentences:
        sentence_search = BM25().fit([sentence for sentence, _ in sentences])
        ranked = [
            sentences[index]
            for index, _ in sentence_search.search(question, limit=3)
        ]

    if ranked:
        text = "In simple terms, " + " ".join(
            f"{sentence} [{citation}]" for sentence, citation in ranked
        )
        citations = list(dict.fromkeys(citation for _, citation in ranked))
    else:
        text = (
            "I found relevant repository evidence, but not enough explanatory prose "
            "to summarize it simply. Please review the retrieved source excerpts below."
        )
        citations = []
    return GenerationResult(
        text=text,
        provider="offline-deterministic",
        citations=citations,
    )
