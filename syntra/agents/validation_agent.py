from pathlib import Path

from syntra.agents.base import SyntraAgent
from syntra.db.models import ValidationStatus
from syntra.services.validation import ValidationEngine


class ValidationAgent(SyntraAgent):
    name = "Validation Agent"
    instructions = "Run available repository validation commands."

    def __init__(self, validation_engine: ValidationEngine):
        self.validation_engine = validation_engine

    def validate(self, repo_dir: Path, runtimes: list[str]) -> tuple[ValidationStatus, str]:
        return self.validation_engine.run(repo_dir, runtimes)
