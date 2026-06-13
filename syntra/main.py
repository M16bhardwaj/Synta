import asyncio
import logging
import threading
from pathlib import Path

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse

from syntra.agents.intake import IntakeAgent
from syntra.agents.implementation import ImplementationAgent
from syntra.agents.planning import PlanningAgent
from syntra.agents.pull_request import PullRequestAgent
from syntra.agents.repository_agent import RepositoryAgent
from syntra.agents.validation_agent import ValidationAgent
from syntra.agents.workflow import BugFixWorkflow
from syntra.api.health import router as health_router
from syntra.api.projects import router as projects_router
from syntra.core.config import get_settings
from syntra.core.logging import configure_logging
from syntra.db.base import SessionLocal, create_db
from syntra.services.bugs import BugService
from syntra.services.git_service import GitService
from syntra.services.github_service import GitHubService
from syntra.services.jobs import JobService
from syntra.services.llm import LLMService
from syntra.services.projects import ProjectService
from syntra.services.repository import RepositoryService
from syntra.services.slack import SlackNotifier, create_slack_app
from syntra.services.validation import ValidationEngine
from syntra.services.job_runner import build_workflow, run_queued_job_once
from syntra.web.routes import router as web_router

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)

github_service = GitHubService(settings.github_token)
WEB_DIR = Path(__file__).resolve().parent / "web"


async def process_bug(bug_id: str, channel: str, slack_client) -> None:
    with SessionLocal() as session:
        notifier = SlackNotifier(slack_client) if slack_client else None
        try:
            bug = await build_workflow(session).run(bug_id)
            if notifier:
                notifier.pr_created(
                    channel=channel,
                    bug_id=bug.bug_id,
                    project_name=bug.project.name,
                    pr_url=bug.pr_url or "",
                    validation_status=bug.validation_result.value if bug.validation_result else "UNKNOWN",
                    summary=f"Created `{bug.branch_name}` for review.",
                )
        except Exception as exc:
            bug = BugService(session).get(bug_id)
            if notifier:
                try:
                    notifier.failed(channel, bug_id, str(exc))
                except Exception:
                    logger.exception("Failed to notify Slack about failure for %s", bug_id)
            logger.exception("Processing failed for %s", bug_id)


def create_app() -> FastAPI:
    if settings.auto_create_db:
        create_db()
    app = FastAPI(title="Syntra MVP")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
    app.include_router(web_router)
    app.include_router(health_router)
    app.include_router(projects_router)

    def enqueue_bug(bug_id: str, channel: str) -> None:
        with SessionLocal() as session:
            JobService(session).enqueue_bug(bug_id)
        if channel != "web" and slack_app:
            worker = threading.Thread(
                target=lambda: asyncio.run(process_bug(bug_id, channel, slack_app.client)),
                name=f"syntra-{bug_id}",
                daemon=True,
            )
            worker.start()

    slack_app = None
    slack_handler = None
    if settings.slack_bot_token and settings.slack_signing_secret:
        slack_app, slack_handler = create_slack_app(
            settings=settings,
            enqueue_bug=enqueue_bug,
            session_factory=SessionLocal,
            github_service=github_service,
        )

    @app.post("/slack/events")
    async def slack_events(request: Request, tasks: BackgroundTasks):
        if not slack_handler:
            return PlainTextResponse("Slack is not configured.", status_code=503)
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            if form.get("command") == "/syntra-fix":
                return handle_syntra_command(form, enqueue_bug)
        return await slack_handler.handle(request)

    @app.get("/internal/jobs/run-once")
    async def run_one_job(request: Request):
        if settings.cron_secret:
            authorization = request.headers.get("authorization", "")
            provided = request.headers.get("x-cron-secret") or request.query_params.get("secret")
            if authorization == f"Bearer {settings.cron_secret}":
                provided = settings.cron_secret
            if provided != settings.cron_secret:
                return PlainTextResponse("Unauthorized", status_code=401)
        with SessionLocal() as session:
            return await run_queued_job_once(session)

    return app


def handle_syntra_command(form, enqueue_bug):
    intake = IntakeAgent()
    try:
        bug_data = intake.parse(str(form.get("text", "")))
        channel = str(form["channel_id"])
        with SessionLocal() as session:
            project = ProjectService(session).get_by_name(bug_data.project)
            if not project:
                return PlainTextResponse(
                    f"Unknown project `{bug_data.project}`. Register it before filing bugs."
                )
            bug = BugService(session).create(project, bug_data)
            bug_id = bug.bug_id
        enqueue_bug(bug_id, channel)
        return PlainTextResponse(f"Syntra started working on {bug_id}.")
    except Exception as exc:
        logger.exception("Failed to accept Slack command")
        return PlainTextResponse(f"Could not start Syntra: {exc}")


app = create_app()


def run() -> None:
    uvicorn.run("syntra.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
