from dataclasses import dataclass
import re

from app.retrieval.bm25 import BM25, focus_query


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    citations: list[str]


def _clean_markdown_line(raw_line: str) -> str:
    line = raw_line.strip()
    if re.match(r"^(?:see|refer to)\b", line, flags=re.IGNORECASE):
        return ""
    line = re.sub(r"<[^>]+>", " ", line)
    line = re.sub(r"^[-*]\s+", "", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", line)
    return line.strip()


def _is_code_like(sentence: str) -> bool:
    return bool(
        re.match(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*=", sentence)
        or re.match(r"^(?:def|class|import|from|return)\b", sentence)
        or re.search(r"\b[A-Za-z_]\w*_[A-Za-z_]\w*\s*\(", sentence)
    )


def _architecture_table_summary(content: str) -> str | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        headers = [
            _clean_markdown_line(cell).lower()
            for cell in line.strip().strip("|").split("|")
        ]
        required = {"layer", "input size", "output size"}
        if not required.issubset(headers):
            continue

        rows = []
        for row_line in lines[index + 1:]:
            if not row_line.strip().startswith("|"):
                break
            cells = [
                _clean_markdown_line(cell)
                for cell in row_line.strip().strip("|").split("|")
            ]
            if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            if len(cells) >= len(headers):
                rows.append(dict(zip(headers, cells)))

        hidden_rows = [
            row for row in rows
            if "hidden" in row["layer"].lower()
            and row["input size"].isdigit()
            and row["output size"].isdigit()
        ]
        output_rows = [
            row for row in rows
            if row["layer"].lower().startswith("output")
            and row["input size"].isdigit()
            and row["output size"].isdigit()
        ]
        if not hidden_rows or not output_rows:
            continue

        hidden_sizes = [row["output size"] for row in hidden_rows]
        hidden_text = " and ".join(hidden_sizes)
        input_size = hidden_rows[0]["input size"]
        output_size = output_rows[-1]["output size"]
        return (
            f"The network maps {input_size} inputs through hidden layers of "
            f"{hidden_text} neurons to {output_size} outputs."
        )
    return None


def generate_answer(question: str, evidence: list[dict]) -> GenerationResult:
    if not evidence:
        return GenerationResult(
            text="Insufficient evidence was retrieved to answer this question.",
            provider="offline-deterministic",
            citations=[],
        )
    sentences: list[tuple[str, str]] = []
    architecture_sentences: list[tuple[str, str]] = []
    seen: set[str] = set()
    architecture_query = any(
        term in question.lower() for term in ("architecture", "design")
    )
    for item in evidence:
        if item["source_type"] not in {"markdown", "text"}:
            continue
        citation = f"{item['source_type']}:{item['file_path']}"
        if architecture_query:
            architecture_summary = _architecture_table_summary(item["content"])
            if architecture_summary:
                architecture_sentences.append((architecture_summary, citation))
        in_code_block = False
        for raw_line in item["content"].splitlines():
            line = raw_line.strip()
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line or line.startswith("#") or line.startswith("|"):
                continue
            line = _clean_markdown_line(line)
            if not line:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                sentence = sentence.strip()
                if sentence.lower().startswith("[x]"):
                    continue
                if _is_code_like(sentence):
                    continue
                if 45 <= len(sentence) <= 360 and sentence not in seen:
                    sentences.append((sentence, citation))
                    seen.add(sentence)

    if architecture_sentences:
        sentences = architecture_sentences

    ranked = []
    if sentences:
        sentence_search = BM25().fit([sentence for sentence, _ in sentences])
        summary_query = focus_query(question)
        if "architecture" in question.lower() or "design" in question.lower():
            summary_query += " system components design pipeline processing flow model layers input hidden output"
        ranked = [
            sentences[index]
            for index, _ in sentence_search.search(summary_query, limit=3)
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
