import json

from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import GITHUB_TOKEN
from app.github.repository_url import parse_public_github_url
from app.ingestion.chunking import chunk_markdown, chunk_plaintext, chunk_python
from app.retrieval.bm25 import BM25, focus_query
from app.retrieval.embeddings import embed_text
from app.retrieval.rrf import reciprocal_rank_fusion


SUPPORTED_EXTENSIONS = {".md", ".py", ".txt", ".json"}
MAX_FILE_BYTES = 250_000
MAX_FILES_PER_QUERY = 12


def _github_request(url: str, accept: str) -> bytes:
    headers = {
        "Accept": accept,
        "User-Agent": "ImpactLens",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub request failed for {url}: {exc}") from exc


def _selected_paths(tree: list[dict], query: str) -> list[dict]:
    candidates = [
        item for item in tree
        if item.get("type") == "blob"
        and item.get("size", MAX_FILE_BYTES + 1) <= MAX_FILE_BYTES
        and any(item["path"].lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)
        and not any(
            part.lower() in {"node_modules", "vendor", "dist", "build", ".git"}
            for part in item["path"].split("/")
        )
    ]
    if not candidates:
        return []

    ranker = BM25().fit([item["path"] for item in candidates])
    ranked = [candidates[index] for index, _ in ranker.search(query, limit=MAX_FILES_PER_QUERY)]
    readmes = [
        item for item in candidates
        if item["path"].split("/")[-1].lower().startswith("readme.")
    ]
    selected: dict[str, dict] = {item["path"]: item for item in readmes[:2]}
    selected.update({item["path"]: item for item in ranked})
    return list(selected.values())[:MAX_FILES_PER_QUERY]


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _intent_ranking(chunks: list[dict], query: str) -> list[str]:
    normalized_query = query.lower()
    if "architecture" not in normalized_query and "design" not in normalized_query:
        return []
    section_order = (
        "network structure",
        "layer design",
        "system architecture",
        "model architecture",
        "architecture overview",
        "data flow",
        "component",
    )
    ranked = []
    for section in section_order:
        ranked.extend(
            item["chunk_id"] for item in chunks
            if section in (item["symbol_name"] or "").lower()
        )
    return list(dict.fromkeys(ranked))


def retrieve_github_repository(remote_url: str, query: str, limit: int = 10) -> list[dict]:
    repository_id, owner, repository = parse_public_github_url(remote_url)
    api_base = f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
    repository_info = json.loads(
        _github_request(api_base, "application/vnd.github+json").decode("utf-8")
    )
    branch = repository_info["default_branch"]
    tree_url = f"{api_base}/git/trees/{quote(branch, safe='')}?recursive=1"
    tree_data = json.loads(
        _github_request(tree_url, "application/vnd.github+json").decode("utf-8")
    )
    if tree_data.get("truncated"):
        raise RuntimeError(
            "GitHub truncated the repository file listing; use a local clone/index for this large repository."
        )

    search_query = focus_query(query)
    paths = _selected_paths(tree_data.get("tree", []), search_query)
    chunks = []
    for item in paths:
        path = item["path"]
        extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        raw_url = (
            f"https://raw.githubusercontent.com/{quote(owner)}/{quote(repository)}/"
            f"{quote(branch, safe='')}/{quote(path, safe='/')}"
        )
        content = _github_request(raw_url, "application/octet-stream").decode(
            "utf-8", errors="replace"
        )
        if extension == ".py":
            file_chunks = chunk_python(content, path)
            source_type = "python"
        elif extension == ".md":
            file_chunks = chunk_markdown(content, path)
            source_type = "markdown"
        else:
            file_chunks = chunk_plaintext(content, path)
            source_type = "text"
        for chunk in file_chunks:
            chunks.append({
                "chunk_id": f"github:{repository_id}:{chunk.chunk_id}",
                "file_path": f"github.com/{owner}/{repository}/{path}",
                "symbol_name": chunk.symbol_name,
                "source_type": source_type,
                "content": chunk.content,
            })

    if not chunks:
        return []
    bm25 = BM25().fit([item["content"] for item in chunks])
    sparse = [
        chunks[index]["chunk_id"]
        for index, _ in bm25.search(search_query, limit=max(limit * 2, 20))
    ]
    heading_search = BM25().fit([
        item["symbol_name"] or item["file_path"] for item in chunks
    ])
    heading_ranking = [
        chunks[index]["chunk_id"]
        for index, _ in heading_search.search(search_query, limit=max(limit * 2, 20))
    ]
    query_vector = embed_text(search_query)
    dense_scores = [
        (item["chunk_id"], _cosine(query_vector, embed_text(item["content"])))
        for item in chunks
    ]
    dense = [
        chunk_id for chunk_id, _ in sorted(
            dense_scores, key=lambda score: (-score[1], score[0])
        )[:max(limit * 2, 20)]
    ]
    intent_ranking = _intent_ranking(chunks, query)
    by_id = {item["chunk_id"]: item for item in chunks}
    fused = reciprocal_rank_fusion(
        [dense, sparse, heading_ranking, intent_ranking]
    )
    if intent_ranking:
        scores = dict(fused)
        ordered_ids = intent_ranking + [
            chunk_id for chunk_id, _ in fused if chunk_id not in intent_ranking
        ]
        fused = [(chunk_id, scores.get(chunk_id, 0.0)) for chunk_id in ordered_ids]
    return [
        {**by_id[chunk_id], "rrf_score": score}
        for chunk_id, score in fused[:limit]
    ]
