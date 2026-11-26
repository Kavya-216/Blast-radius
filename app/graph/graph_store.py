from app.database.connection import database


def store_symbols_and_relationships(repository_id: str, symbols, relationships, connection=None) -> None:
    owns_connection = connection is None
    if owns_connection:
        from contextlib import nullcontext
        context = database()
    else:
        from contextlib import nullcontext
        context = nullcontext(connection)
    with context as connection:
        for symbol in symbols:
            connection.execute(
                "INSERT OR REPLACE INTO symbols "
                "(repository_id, stable_id, file_path, qualified_name, symbol_type, start_line, end_line) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    repository_id,
                    symbol.stable_id,
                    symbol.file_path,
                    symbol.qualified_name,
                    symbol.symbol_type,
                    symbol.start_line,
                    symbol.end_line,
                ),
            )
        for relationship in relationships:
            connection.execute(
                "INSERT INTO relationships "
                "(repository_id, source_id, target_id, relationship_type, evidence_source, "
                "extraction_method, evidence_strength) "
                "VALUES (?, ?, ?, ?, ?, ?, 'static')",
                (
                    repository_id,
                    relationship.source_id,
                    relationship.target_id,
                    relationship.relationship_type,
                    relationship.evidence_source,
                    relationship.extraction_method,
                ),
            )
        if owns_connection:
            connection.commit()
