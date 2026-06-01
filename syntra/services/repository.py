from pathlib import Path


LANGUAGE_MARKERS = {
    "package.json": ("node", "JavaScript/TypeScript"),
    "pyproject.toml": ("python", "Python"),
    "requirements.txt": ("python", "Python"),
    "pom.xml": ("java-maven", "Java"),
    "build.gradle": ("java-gradle", "Java"),
    "go.mod": ("go", "Go"),
}


class RepositoryService:
    def analyze(self, repo_dir: Path, bug_text: str) -> dict:
        markers = [name for name in LANGUAGE_MARKERS if (repo_dir / name).exists()]
        detected = [LANGUAGE_MARKERS[name] for name in markers]
        files = self._candidate_files(repo_dir, bug_text)
        return {
            "markers": markers,
            "languages": sorted({item[1] for item in detected}),
            "runtimes": sorted({item[0] for item in detected}),
            "candidate_files": files,
        }

    def _candidate_files(self, repo_dir: Path, bug_text: str) -> list[str]:
        words = {
            word.lower()
            for word in bug_text.replace("-", " ").replace("_", " ").split()
            if len(word) >= 4
        }
        candidates: list[tuple[int, str]] = []
        for path in repo_dir.rglob("*"):
            if self._skip(path, repo_dir):
                continue
            score = 0
            lower_name = path.name.lower()
            for word in words:
                if word in lower_name:
                    score += 3
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:120_000].lower()
            except OSError:
                continue
            for word in words:
                if word in text:
                    score += 1
            if score:
                candidates.append((score, path.relative_to(repo_dir).as_posix()))
        return [path for _, path in sorted(candidates, reverse=True)[:12]]

    def _skip(self, path: Path, repo_dir: Path) -> bool:
        if not path.is_file():
            return True
        relative = path.relative_to(repo_dir)
        blocked = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
        return any(part in blocked for part in relative.parts)
