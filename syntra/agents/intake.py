import re

from syntra.agents.base import SyntraAgent
from syntra.schemas.bugs import BugIntake


class IntakeAgent(SyntraAgent):
    name = "Intake Agent"
    instructions = "Parse Slack bug reports into project, title, description, and priority."

    def parse(self, text: str) -> BugIntake:
        values: dict[str, str] = {}
        for line in text.splitlines():
            if "=" not in line or self._looks_inline(line):
                continue
            key, value = line.split("=", 1)
            values[key.strip().lower()] = value.strip()

        for key in ("project", "title", "description", "priority"):
            if key in values:
                continue
            match = re.search(
                rf"{key}\s*=\s*(.+?)(?=\s+(?:project|title|description|priority)=|$)",
                text,
                flags=re.I | re.S,
            )
            if match:
                values[key] = match.group(1).strip()

        return BugIntake(
            project=values["project"],
            title=values["title"],
            description=values["description"],
            priority=values.get("priority", "medium"),
        )

    def _looks_inline(self, line: str) -> bool:
        return sum(1 for key in ("project=", "title=", "description=", "priority=") if key in line.lower()) > 1
