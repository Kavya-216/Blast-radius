import math

from app.database.connection import database
from app.retrieval.bm25 import BM25
from app.retrieval.embeddings import embed_text
from app.retrieval.rrf import reciprocal_rank_fusion


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def retrieve(repository_id: str, query: str, limit: int = 10) -> list[dict]:
    with database() as connection:
        repository = connection.execute(
            "SELECT local_path, remote_url FROM repositories WHERE repository_id=?",
            (repository_id,),
        ).fetchone()
        if repository and repository["remote_url"] and not repository["local_path"]:
            remote_url = repository["remote_url"]
            rows = []
        else:
            remote_url = None
        rows = connection.execute(
            "SELECT chunk_id, file_path, symbol_name, source_type, content "
            "FROM chunks WHERE repository_id=?",
            (repository_id,),
        ).fetchall() if remote_url is None else []

    if remote_url:
        from app.retrieval.github_retriever import retrieve_github_repository
        return retrieve_github_repository(remote_url, query, limit)
    if not rows:
        return []
    bm25 = BM25().fit([row["content"] for row in rows])
    sparse_hits = bm25.search(query, limit=max(limit * 2, 20))
    sparse_ranking = [rows[index]["chunk_id"] for index, _ in sparse_hits]

    query_embedding = embed_text(query)
    dense_scores = [
        (row["chunk_id"], cosine(query_embedding, embed_text(row["content"])))
        for row in rows
    ]
    dense_ranking = [
        chunk_id for chunk_id, _ in sorted(
            dense_scores, key=lambda item: (-item[1], item[0])
        )[: max(limit * 2, 20)]
    ]

    fused = reciprocal_rank_fusion([dense_ranking, sparse_ranking])[:limit]
    row_by_id = {row["chunk_id"]: row for row in rows}
    results = []
    for chunk_id, rrf_score in fused:
        row = row_by_id[chunk_id]
        results.append({
            "chunk_id": row["chunk_id"],
            "file_path": row["file_path"],
            "symbol_name": row["symbol_name"],
            "source_type": row["source_type"],
            "content": row["content"],
            "rrf_score": rrf_score,
        })
    return results
