import re
import time
from pathlib import Path

import jwt
from github import Github
from github.Repository import Repository

from syntra.core.config import get_settings


class GitHubService:
    def __init__(self, token: str):
        self.client = Github(token)

    def repo_from_url(self, repository_url: str) -> Repository:
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", repository_url)
        if not match:
            raise ValueError(f"Unsupported GitHub URL: {repository_url}")
        return self.client.get_repo(f"{match.group('owner')}/{match.group('repo')}")

    def create_pr(
        self,
        repository_url: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> tuple[str, int]:
        repo = self.repo_from_url(repository_url)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return pr.html_url, pr.number

    def merge_pr(self, repository_url: str, pr_number: int, message: str) -> str:
        repo = self.repo_from_url(repository_url)
        pr = repo.get_pull(pr_number)
        if not pr:
            raise ValueError(f"PR {pr_number} not found")
        result = pr.merge(commit_message=message)
        if not result.merged:
            raise RuntimeError(result.message)
        return result.sha

    def installation_token(self, installation_id: str) -> str:
        settings = get_settings()
        if not settings.github_app_id or not settings.github_app_private_key_path:
            raise ValueError("GitHub App credentials are not configured.")
        private_key = Path(settings.github_app_private_key_path).read_text(encoding="utf-8")
        now = int(time.time())
        app_jwt = jwt.encode(
            {"iat": now - 60, "exp": now + 600, "iss": settings.github_app_id},
            private_key,
            algorithm="RS256",
        )
        app_client = Github(app_jwt)
        installation = app_client.get_app().get_installation(int(installation_id))
        return installation.get_access_token().token
