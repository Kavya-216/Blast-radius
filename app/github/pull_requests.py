from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import GITHUB_TOKEN
from app.github.repository_url import parse_public_github_url


MAX_PULL_REQUEST_DIFF_BYTES = 1_000_000
MAX_DIFF_EVIDENCE_CHARS = 20_000
MAX_CHANGE_CONTEXT_CHARS = 10_000


def fetch_pull_request_diff(remote_url: str, pull_request_number: int) -> dict:
    if pull_request_number < 1:
        raise ValueError("pull_request_number must be a positive integer")

    _, owner, repository = parse_public_github_url(remote_url)
    api_url = (
        f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
        f"/pulls/{pull_request_number}"
    )
    headers = {
        "Accept": "application/vnd.github.diff",
        "User-Agent": "ImpactLens",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        with urlopen(Request(api_url, headers=headers), timeout=20) as response:
            diff_bytes = response.read(MAX_PULL_REQUEST_DIFF_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404:
            message = "Pull request not found or not accessible in the connected repository."
        elif exc.code in (403, 429):
            message = "GitHub denied the pull request request or its API rate limit was reached."
        else:
            message = f"GitHub could not return the pull request diff (HTTP {exc.code})."
        raise RuntimeError(message) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach GitHub to fetch the pull request diff: {exc}") from exc

    if len(diff_bytes) > MAX_PULL_REQUEST_DIFF_BYTES:
        raise RuntimeError("The pull request diff exceeds the 1 MB analysis limit.")

    diff = diff_bytes.decode("utf-8", errors="replace")
    lines = diff.splitlines()
    change_lines = [
        line for line in lines
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    ]
    full_change_context = "\n".join(change_lines)
    change_context = full_change_context[:MAX_CHANGE_CONTEXT_CHARS]
    return {
        "changed_files": _changed_files(diff),
        "additions": sum(
            1 for line in lines
            if line.startswith("+") and not line.startswith("+++")
        ),
        "deletions": sum(
            1 for line in lines
            if line.startswith("-") and not line.startswith("---")
        ),
        "diff": diff,
        "diff_excerpt": diff[:MAX_DIFF_EVIDENCE_CHARS],
        "diff_truncated": len(diff) > MAX_DIFF_EVIDENCE_CHARS,
        "change_context": change_context,
        "change_context_truncated": len(full_change_context) > MAX_CHANGE_CONTEXT_CHARS,
    }


def _changed_files(diff: str) -> list[str]:
    changed_files = []
    old_path = None
    for line in diff.splitlines():
        if line.startswith("diff --git a/") and " b/" in line:
            old_path, new_path = line.removeprefix("diff --git a/").split(" b/", 1)
            changed_files.append(new_path)
        elif line.startswith("--- a/"):
            old_path = line[6:]
        elif line.startswith("+++ b/"):
            changed_files.append(line[6:])
        elif line.startswith("rename to "):
            changed_files.append(line.removeprefix("rename to "))
        elif line == "+++ /dev/null" and old_path:
            changed_files.append(old_path)

    return list(dict.fromkeys(path.strip('"') for path in changed_files if path))
