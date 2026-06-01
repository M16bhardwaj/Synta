import re

from github import Github
from github.Repository import Repository


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
