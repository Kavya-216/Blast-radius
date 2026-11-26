import json
import os
from urllib import request

from app.config import GITHUB_TOKEN


class GitHubClient:
    def __init__(self, token: str | None = GITHUB_TOKEN):
        self.token = token

    def get(self, url: str) -> dict:
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not configured")
        req = request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
