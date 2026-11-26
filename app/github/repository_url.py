import re
from urllib.parse import urlparse


def parse_public_github_url(remote_url: str) -> tuple[str, str, str]:
    parsed = urlparse(remote_url.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Only public HTTPS repositories hosted at github.com are supported")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise ValueError("Use a repository URL in the form https://github.com/owner/repository")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+", repository
    ):
        raise ValueError("The GitHub URL contains an invalid owner or repository name")
    repository_id = f"github-{owner}-{repository}".lower()
    canonical_url = f"https://github.com/{owner}/{repository}.git"
    return repository_id, owner, repository
