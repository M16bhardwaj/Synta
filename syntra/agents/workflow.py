import logging

from sqlalchemy.orm import Session

from syntra.agents.implementation import ImplementationAgent
from syntra.agents.planning import PlanningAgent
from syntra.agents.pull_request import PullRequestAgent
from syntra.agents.repository_agent import RepositoryAgent
from syntra.agents.validation_agent import ValidationAgent
from syntra.db.models import Bug
from syntra.services.bugs import BugService
from syntra.services.git_service import GitService

logger = logging.getLogger(__name__)


class BugFixWorkflow:
    def __init__(
        self,
        session: Session,
        git_service: GitService,
        repository_agent: RepositoryAgent,
        planning_agent: PlanningAgent,
        implementation_agent: ImplementationAgent,
        validation_agent: ValidationAgent,
        pull_request_agent: PullRequestAgent,
    ):
        self.session = session
        self.bugs = BugService(session)
        self.git_service = git_service
        self.repository_agent = repository_agent
        self.planning_agent = planning_agent
        self.implementation_agent = implementation_agent
        self.validation_agent = validation_agent
        self.pull_request_agent = pull_request_agent

    async def run(self, bug_id: str) -> Bug:
        bug = self.bugs.get(bug_id)
        if not bug:
            raise ValueError(f"Bug not found: {bug_id}")
        self.bugs.mark_started(bug)
        try:
            repo, repo_dir, branch_name = self.git_service.clone_for_bug(bug.project, bug)
            bug_text = f"{bug.title}\n{bug.description}"
            analysis = self.repository_agent.analyze(repo_dir, bug_text)
            plan = self.planning_agent.plan(
                {
                    "bug_id": bug.bug_id,
                    "title": bug.title,
                    "description": bug.description,
                    "priority": bug.priority,
                },
                analysis,
            )
            summary = await self.implementation_agent.implement(
                {
                    "bug_id": bug.bug_id,
                    "title": bug.title,
                    "description": bug.description,
                    "priority": bug.priority,
                },
                analysis,
                plan,
                repo_dir,
            )
            validation, validation_output = self.validation_agent.validate(
                repo_dir, analysis.get("runtimes", [])
            )
            pr_url, pr_number, _ = self.pull_request_agent.create(
                repo,
                bug.project,
                bug,
                branch_name,
                summary,
                analysis,
                plan,
                validation,
                validation_output,
            )
            self.bugs.mark_pr_created(
                bug, branch_name, pr_url, pr_number, validation, validation_output
            )
            return bug
        except Exception as exc:
            logger.exception("Bug workflow failed for %s", bug_id)
            self.bugs.mark_failed(bug, str(exc))
            raise
