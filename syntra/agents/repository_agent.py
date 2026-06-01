from pathlib import Path

from syntra.agents.base import SyntraAgent
from syntra.services.repository import RepositoryService


class RepositoryAgent(SyntraAgent):
    name = "Repository Agent"
    instructions = "Detect language, framework markers, repository structure, and likely files."

    def __init__(self, repository_service: RepositoryService):
        self.repository_service = repository_service

    def analyze(self, repo_dir: Path, bug_text: str) -> dict:
        return self.repository_service.analyze(repo_dir, bug_text)
