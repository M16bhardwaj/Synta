import asyncio
import threading

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from github import Github
from sqlalchemy import desc, select

from syntra.core.config import get_settings
from syntra.db.base import SessionLocal
from syntra.db.models import Bug, Project
from syntra.schemas.bugs import BugIntake
from syntra.schemas.projects import ProjectCreate
from syntra.services.bugs import BugService
from syntra.services.projects import ProjectService

settings = get_settings()
templates = Jinja2Templates(directory="syntra/web/templates")
router = APIRouter()


def _github_status() -> dict:
    try:
        user = Github(settings.github_token).get_user()
        return {"connected": True, "login": user.login}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


def _slack_url() -> str:
    return f"{settings.app_base_url.rstrip('/')}/slack/events"


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(
        request,
        "landing.html",
        {"request": request, "settings": settings, "github": _github_status()},
    )


@router.get("/app", response_class=HTMLResponse)
def dashboard(request: Request):
    with SessionLocal() as session:
        projects = session.scalars(select(Project).order_by(Project.name)).all()
        bugs = session.scalars(select(Bug).order_by(desc(Bug.created_at)).limit(8)).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "projects": projects,
            "bugs": bugs,
            "github": _github_status(),
            "slack_url": _slack_url(),
            "llm_provider": settings.llm_provider,
        },
    )


@router.get("/app/projects", response_class=HTMLResponse)
def projects_page(request: Request):
    with SessionLocal() as session:
        projects = session.scalars(select(Project).order_by(Project.name)).all()
    return templates.TemplateResponse(
        request,
        "projects.html",
        {"request": request, "projects": projects},
    )


@router.post("/app/projects")
def create_project(
    name: str = Form(...),
    repository_url: str = Form(...),
    default_branch: str = Form("main"),
):
    with SessionLocal() as session:
        ProjectService(session).register(
            ProjectCreate(name=name, repository_url=repository_url, default_branch=default_branch)
        )
    return RedirectResponse("/app/projects", status_code=303)


@router.get("/app/bugs", response_class=HTMLResponse)
def bugs_page(request: Request):
    with SessionLocal() as session:
        bugs = session.scalars(select(Bug).order_by(desc(Bug.created_at))).all()
    return templates.TemplateResponse(request, "bugs.html", {"request": request, "bugs": bugs})


@router.get("/app/bugs/new", response_class=HTMLResponse)
def new_bug_page(request: Request):
    with SessionLocal() as session:
        projects = session.scalars(select(Project).order_by(Project.name)).all()
    return templates.TemplateResponse(
        request, "new_bug.html", {"request": request, "projects": projects}
    )


@router.post("/app/bugs")
def create_bug_from_web(
    project_name: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    priority: str = Form("medium"),
):
    with SessionLocal() as session:
        project = ProjectService(session).get_by_name(project_name)
        if not project:
            return RedirectResponse("/app/bugs/new?error=project", status_code=303)
        bug = BugService(session).create(
            project,
            BugIntake(
                project=project_name,
                title=title,
                description=description,
                priority=priority,
            ),
        )
        bug_id = bug.bug_id

    from syntra.main import process_bug

    worker = threading.Thread(
        target=lambda: asyncio.run(process_bug(bug_id, "web", None)),
        name=f"syntra-web-{bug_id}",
        daemon=True,
    )
    worker.start()
    return RedirectResponse(f"/app/bugs?created={bug_id}", status_code=303)


@router.get("/app/github", response_class=HTMLResponse)
def github_page(request: Request):
    return templates.TemplateResponse(
        request,
        "github.html",
        {"request": request, "github": _github_status()},
    )


@router.get("/app/slack", response_class=HTMLResponse)
def slack_page(request: Request):
    return templates.TemplateResponse(
        request,
        "slack.html",
        {"request": request, "slack_url": _slack_url()},
    )
