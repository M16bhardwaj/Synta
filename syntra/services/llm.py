import json
from pathlib import Path
from typing import Any

import httpx


class LLMService:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key

    async def implementation_patch(
        self,
        bug: dict[str, Any],
        analysis: dict[str, Any],
        plan: dict[str, Any],
        repo_dir: Path,
    ) -> dict[str, str]:
        if self.provider.lower() == "mock":
            return self._mock_patch(bug, repo_dir)

        files = {}
        for relative in plan.get("files_to_modify", [])[:6]:
            path = repo_dir / relative
            if path.exists() and path.is_file():
                files[relative] = path.read_text(encoding="utf-8", errors="ignore")[:20_000]

        prompt = {
            "instruction": (
                "Return JSON only: {\"files\": {\"relative/path\": \"full replacement content\"}, "
                "\"summary\": \"short summary\"}. Make the smallest bug fix. Do not refactor."
            ),
            "bug": bug,
            "repository_analysis": analysis,
            "implementation_plan": plan,
            "file_contents": files,
        }
        if self.provider.lower() != "openai":
            raise ValueError(f"Unsupported LLM_PROVIDER for MVP: {self.provider}")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "gpt-4.1-mini",
                    "messages": [
                        {"role": "system", "content": "You are a careful senior software engineer."},
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _mock_patch(self, bug: dict[str, Any], repo_dir: Path) -> dict[str, str]:
        readme = self._find_readme(repo_dir)
        if readme is None:
            readme = repo_dir / "SYNTRA_FIX_NOTES.md"
            original = "# Syntra Fix Notes\n"
            relative = readme.name
        else:
            original = readme.read_text(encoding="utf-8", errors="ignore")
            relative = readme.relative_to(repo_dir).as_posix()

        note = (
            "\n\n"
            "<!-- syntra-mock-fix -->\n"
            "## Syntra Mock Fix\n"
            f"- Bug: {bug.get('bug_id', 'unknown')}\n"
            f"- Title: {bug.get('title', 'Untitled bug')}\n"
            f"- Description: {bug.get('description', '')}\n"
        )
        if "<!-- syntra-mock-fix -->" in original:
            content = original
        else:
            content = original.rstrip() + note + "\n"
        return {
            "files": {relative: content},
            "summary": (
                "Mock LLM mode added a small Syntra note so the branch, validation, "
                "commit, push, PR, and approval workflow can be tested without an LLM key."
            ),
        }

    def _find_readme(self, repo_dir: Path) -> Path | None:
        for name in ("README.md", "readme.md", "README.txt", "README"):
            path = repo_dir / name
            if path.exists() and path.is_file():
                return path
        return None
