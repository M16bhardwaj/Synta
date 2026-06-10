import logging

from sqlalchemy.orm import Session

from syntra.agents.implementation import ImplementationAgent
from syntra.agents.planning import PlanningAgent
from syntra.agents.pull_request import PullRequestAgent
from syntra.agents.repository_agent import RepositoryAgent
from syntra.agents.validation_agent import ValidationAgent
from syntra.agents.workflow import BugFixWorkflow
from syntra.core.config import get_settings
from syntra.services.bugs import BugService
from syntra.services.git_service import GitService
from syntra.services.github_service import GitHubService
from syntra.services.jobs import JobService
from syntra.services.llm import LLMService
from syntra.services.repository import RepositoryService
from syntra.services.validation import ValidationEngine

logger = logging.getLogger(__name__)


def build_workflow(session: Session) -> BugFixWorkflow:
    settings = get_settings()
    github_service = GitHubService(settings.github_token)
    git_service = GitService(settings.workspace_dir, settings.github_token)
    return BugFixWorkflow(
        session=session,
        git_service=git_service,
        repository_agent=RepositoryAgent(RepositoryService()),
        planning_agent=PlanningAgent(),
        implementation_agent=ImplementationAgent(
            LLMService(settings.llm_provider, settings.llm_api_key)
        ),
        validation_agent=ValidationAgent(ValidationEngine()),
        pull_request_agent=PullRequestAgent(git_service, github_service),
    )


async def run_queued_job_once(session: Session) -> dict:
    jobs = JobService(session)
    job = jobs.next_job()
    if not job:
        return {"processed": False}
    try:
        bug = await build_workflow(session).run(job.bug_id)
        jobs.complete(job)
        return {"processed": True, "job_id": job.id, "bug_id": bug.bug_id, "status": bug.status.value}
    except Exception as exc:
        bug = BugService(session).get(job.bug_id)
        if bug:
            BugService(session).mark_failed(bug, str(exc))
        jobs.fail(job, str(exc))
        logger.exception("Queued job failed: %s", job.id)
        return {"processed": True, "job_id": job.id, "bug_id": job.bug_id, "error": str(exc)}
