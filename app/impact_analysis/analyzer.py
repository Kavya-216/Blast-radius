import subprocess
from pathlib import Path

from app.retrieval.hybrid_retriever import retrieve
from app.graph.traversal import neighbors


def analyze_diff(local_path: str, base_sha: str, head_sha: str) -> dict:
    root = Path(local_path).resolve()
    if not root.is_dir():
        raise ValueError("local_path is not a directory")
    for sha in (base_sha, head_sha):
        if not sha or len(sha) > 64 or any(ch not in "0123456789abcdefABCDEF" for ch in sha):
            raise ValueError("base_sha and head_sha must be hexadecimal Git object names")
    proc = subprocess.run(
        ["git", "diff", "--name-status", "-z", base_sha, head_sha],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    entries = [part for part in proc.stdout.split("\0") if part]
    changed_files = []
    index = 0
    while index < len(entries):
        status = entries[index]
        if status.startswith("R") and index + 2 < len(entries):
            changed_files.append({"status": status, "old_path": entries[index + 1], "path": entries[index + 2]})
            index += 3
        elif index + 1 < len(entries):
            changed_files.append({"status": status, "path": entries[index + 1]})
            index += 2
        else:
            index += 1
    return {"changed_files": changed_files}
