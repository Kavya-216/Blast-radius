import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Symbol:
    stable_id: str
    file_path: str
    qualified_name: str
    symbol_type: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Relationship:
    source_id: str
    target_id: str
    relationship_type: str
    evidence_source: str
    extraction_method: str


def analyze_python_file(repository_id: str, file_path: str, content: str):
    tree = ast.parse(content, filename=file_path)
    symbols: list[Symbol] = []
    relationships: list[Relationship] = []
    module_prefix = file_path.replace("/", ".").removesuffix(".py")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            type_name = "class" if isinstance(node, ast.ClassDef) else "function"
            qualified = f"{module_prefix}.{node.name}"
            stable = f"{repository_id}:{file_path}:{type_name}:{qualified}"
            symbols.append(Symbol(
                stable_id=stable,
                file_path=file_path,
                qualified_name=qualified,
                symbol_type=type_name,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            ))

        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                source = f"{repository_id}:{file_path}:module:{module_prefix}"
                relationships.append(Relationship(
                    source_id=source,
                    target_id=f"{repository_id}:module:{target}",
                    relationship_type="IMPORTS",
                    evidence_source=file_path,
                    extraction_method="ast.Import",
                ))
        if isinstance(node, ast.ImportFrom) and node.module:
            source = f"{repository_id}:{file_path}:module:{module_prefix}"
            relationships.append(Relationship(
                source_id=source,
                target_id=f"{repository_id}:module:{node.module}",
                relationship_type="IMPORTS",
                evidence_source=file_path,
                extraction_method="ast.ImportFrom",
            ))
        if isinstance(node, ast.Call):
            parent_symbol = f"{module_prefix}.module"
            for candidate in ast.walk(tree):
                if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if candidate.lineno <= node.lineno <= getattr(candidate, "end_lineno", candidate.lineno):
                        parent_symbol = f"{module_prefix}.{candidate.name}"
                        break
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    called_name = f"{node.func.value.id}.{node.func.attr}"
            else:
                continue
            relationships.append(Relationship(
                source_id=f"{repository_id}:{file_path}:function:{parent_symbol}",
                target_id=f"{repository_id}:symbol:{called_name}",
                relationship_type="CALLS",
                evidence_source=file_path,
                extraction_method="ast.Call(Name)",
            ))
    return symbols, relationships
