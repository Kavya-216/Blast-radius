import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_type: str
    source_id: str
    file_path: str
    symbol_name: str | None
    content_hash: str
    content: str


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chunk_python(text: str, file_path: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    lines = text.splitlines()
    headings = re.compile(r"^(class|def|async def)\s+([A-Za-z_][\w]*)")
    starts: list[tuple[int, str | None]] = []
    for index, line in enumerate(lines):
        match = headings.match(line.strip())
        if match:
            starts.append((index, match.group(2)))
    if not starts:
        return [Chunk(
            chunk_id=f"{file_path}:module",
            source_type="python",
            source_id=file_path,
            file_path=file_path,
            symbol_name=None,
            content_hash=content_hash(text),
            content=text,
        )]
    for position, (start, symbol) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        chunks.append(Chunk(
            chunk_id=f"{file_path}:{symbol}",
            source_type="python",
            source_id=file_path,
            file_path=file_path,
            symbol_name=symbol,
            content_hash=content_hash(content),
            content=content,
        ))
    return chunks


def chunk_markdown(text: str, file_path: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_heading = "document"
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current:
                content = "\n".join(current).strip()
                chunks.append(_make_chunk(file_path, "markdown", current_heading, content))
                current = []
            current_heading = line.lstrip("# ").strip()
        current.append(line)
    if current:
        content = "\n".join(current).strip()
        chunks.append(_make_chunk(file_path, "markdown", current_heading, content))
    return chunks or [_make_chunk(file_path, "markdown", "document", text)]


def chunk_plaintext(text: str, file_path: str) -> list[Chunk]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []
    return [_make_chunk(file_path, "text", f"paragraph-{index + 1}", part)
            for index, part in enumerate(paragraphs)]


def _make_chunk(file_path: str, source_type: str, symbol_name: str, content: str) -> Chunk:
    return Chunk(
        chunk_id=f"{file_path}:{symbol_name}",
        source_type=source_type,
        source_id=file_path,
        file_path=file_path,
        symbol_name=symbol_name,
        content_hash=content_hash(content),
        content=content,
    )
