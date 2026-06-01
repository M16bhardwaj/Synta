import re
import shutil
from pathlib import Path

from git import Repo

from syntra.db.models import Bug, Project


def slugify(value: str, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:max_length].strip("-") or "bug"


class GitService:
    def __init__(self, workspace_dir: Path, github_token: str | None = None):
        self.workspace_dir = workspace_dir
        self.github_token = github_token

    def clone_for_bug(self, project: Project, bug: Bug) -> tuple[Repo, Path, str]:
        repo_dir = self.workspace_dir / bug.bug_id
        if repo_dir.exists():
            shutil.rmtree(repo_dir)

        clone_url = self._authenticated_url(project.repository_url)
        repo = Repo.clone_from(clone_url, repo_dir)
        repo.remotes.origin.set_url(clone_url)
        repo.git.checkout(project.default_branch)
        repo.remotes.origin.pull(project.default_branch)

        branch_name = f"bugfix/{bug.bug_id.lower()}-{slugify(bug.title)}"
        repo.git.checkout("-b", branch_name)
        return repo, repo_dir, branch_name

    def commit_all(self, repo: Repo, title: str) -> bool:
        repo.git.add(A=True)
        if not repo.is_dirty(untracked_files=True):
            return False
        repo.index.commit(f"fix: resolve {title}")
        return True

    def push(self, repo: Repo, branch_name: str) -> None:
        repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)

    def _authenticated_url(self, repository_url: str) -> str:
        if not self.github_token or "github.com" not in repository_url:
            return repository_url
        if repository_url.startswith("https://"):
            return repository_url.replace(
                "https://github.com/",
                f"https://x-access-token:{self.github_token}@github.com/",
                1,
            )
        return repository_url
