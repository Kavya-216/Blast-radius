from app.database.connection import database


def neighbors(repository_id: str, symbol_name: str, max_depth: int = 2, limit: int = 20) -> list[dict]:
    with database() as connection:
        rows = connection.execute(
            "SELECT source_id, target_id, relationship_type, evidence_source, "
            "extraction_method, evidence_strength "
            "FROM relationships WHERE repository_id=?",
            (repository_id,),
        ).fetchall()

    adjacency: dict[str, list[dict]] = {}
    for row in rows:
        adjacency.setdefault(row["source_id"], []).append(dict(row))
        adjacency.setdefault(row["target_id"], []).append({
            **dict(row),
            "source_id": row["target_id"],
            "target_id": row["source_id"],
        })

    start_ids = [row["source_id"] for row in rows if symbol_name in row["source_id"]]
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(source_id, 0) for source_id in start_ids]
    results: list[dict] = []
    while queue:
        node_id, depth = queue.pop(0)
        if node_id in visited or depth > max_depth or len(results) >= limit:
            continue
        visited.add(node_id)
        for edge in adjacency.get(node_id, []):
            if edge["target_id"] not in visited:
                results.append(edge)
                if depth + 1 <= max_depth:
                    queue.append((edge["target_id"], depth + 1))
    return results[:limit]
