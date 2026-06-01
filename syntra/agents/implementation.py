from pathlib import Path

from syntra.agents.base import SyntraAgent
from syntra.services.llm import LLMService


class ImplementationAgent(SyntraAgent):
    name = "Implementation Agent"
    instructions = "Modify code minimally to fix the bug."

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def implement(self, bug: dict, analysis: dict, plan: dict, repo_dir: Path) -> str:
        result = await self.llm_service.implementation_patch(bug, analysis, plan, repo_dir)
        changed = result.get("files", {})
        if not changed:
            raise RuntimeError("LLM returned no file changes.")
        for relative, content in changed.items():
            target = (repo_dir / relative).resolve()
            if repo_dir.resolve() not in target.parents and target != repo_dir.resolve():
                raise ValueError(f"Refusing to write outside repository: {relative}")
            target.write_text(content, encoding="utf-8")
        return result.get("summary", "Applied minimal bug fix.")
