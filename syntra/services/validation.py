import subprocess
from dataclasses import dataclass
from pathlib import Path

from syntra.db.models import ValidationStatus


@dataclass
class CommandResult:
    command: str
    available: bool
    passed: bool
    output: str


class ValidationEngine:
    def commands_for(self, repo_dir: Path, runtimes: list[str]) -> list[list[str]]:
        commands: list[list[str]] = []
        if "node" in runtimes:
            commands.extend([["npm", "test"], ["npm", "run", "lint"], ["npm", "run", "build"]])
        if "python" in runtimes:
            commands.append(["pytest"])
        if "java-maven" in runtimes:
            commands.append(["mvn", "test"])
        if "java-gradle" in runtimes:
            commands.append(["gradle", "test"])
        if "go" in runtimes:
            commands.append(["go", "test", "./..."])
        return commands

    def run(self, repo_dir: Path, runtimes: list[str]) -> tuple[ValidationStatus, str]:
        commands = self.commands_for(repo_dir, runtimes)
        if not commands:
            return ValidationStatus.PARTIAL, "No known validation commands found."

        results = [self._run_command(repo_dir, command) for command in commands]
        output = "\n\n".join(
            f"$ {' '.join(result.command)}\n"
            f"available={result.available} passed={result.passed}\n"
            f"{result.output[-4000:]}"
            for result in results
        )
        if any(result.available and not result.passed for result in results):
            return ValidationStatus.FAILED, output
        if any(not result.available for result in results):
            return ValidationStatus.PARTIAL, output
        return ValidationStatus.PASSED, output

    def _run_command(self, repo_dir: Path, command: list[str]) -> CommandResult:
        try:
            completed = subprocess.run(
                command,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            return CommandResult(
                command=command,
                available=True,
                passed=completed.returncode == 0,
                output=(completed.stdout + completed.stderr).strip(),
            )
        except FileNotFoundError as exc:
            return CommandResult(command=command, available=False, passed=False, output=str(exc))
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") + (exc.stderr or "")).strip()
            return CommandResult(command=command, available=True, passed=False, output=output)
