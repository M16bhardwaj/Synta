from git import Repo

from syntra.agents.base import SyntraAgent
from syntra.db.models import Bug, Project, ValidationStatus
from syntra.services.git_service import GitService
from syntra.services.github_service import GitHubService


class PullRequestAgent(SyntraAgent):
    name = "Pull Request Agent"
    instructions = "Commit code, push branch, create a GitHub PR, and summarize the fix."

    def __init__(self, git_service: GitService, github_service: GitHubService):
        self.git_service = git_service
        self.github_service = github_service

    def create(
        self,
        repo: Repo,
        project: Project,
        bug: Bug,
        branch_name: str,
        summary: str,
        analysis: dict,
        plan: dict,
        validation: ValidationStatus,
        validation_output: str,
    ) -> tuple[str, int, str]:
        committed = self.git_service.commit_all(repo, bug.title)
        if not committed:
            raise RuntimeError("No code changes were produced.")
        self.git_service.push(repo, branch_name)
        body = self._body(bug, summary, analysis, plan, validation, validation_output)
        pr_url, pr_number = self.github_service.create_pr(
            project.repository_url,
            title=f"fix: {bug.title}",
            body=body,
            head=branch_name,
            base=project.default_branch,
        )
        return pr_url, pr_number, body

    def _body(
        self,
        bug: Bug,
        summary: str,
        analysis: dict,
        plan: dict,
        validation: ValidationStatus,
        validation_output: str,
    ) -> str:
        files = "\n".join(f"- `{path}`" for path in plan.get("files_to_modify", [])) or "- Unknown"
        return f"""## Bug Summary
{bug.description}

## Root Cause
{plan.get("probable_root_cause", "See implementation notes.")}

## Fix Strategy
{summary}

## Files Modified
{files}

## Validation Results
{validation.value}

```text
{validation_output[-6000:]}
```

## Risk Assessment
Low to medium. The change is intended to be minimal and scoped to the reported bug.

## Human Review Required
This PR must be reviewed and explicitly approved from Slack before merge.
"""
