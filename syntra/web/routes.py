from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import desc, select

from syntra.core.config import get_settings
from syntra.db.base import SessionLocal
from syntra.db.models import (
    AuditEvent,
    Bug,
    BugStatus,
    GitHubInstallation,
    Job,
    Project,
    SlackInstallation,
    MemberRole,
    Workspace,
)
from syntra.schemas.bugs import BugIntake
from syntra.schemas.projects import ProjectCreate
from syntra.services.bugs import BugService
from syntra.services.auth import AuthService
from syntra.services.github_service import GitHubService
from syntra.services.integrations import IntegrationService
from syntra.services.invitations import InvitationService
from syntra.services.jobs import JobService
from syntra.services.projects import ProjectService

settings = get_settings()
WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
router = APIRouter()


def _auth_context(request: Request) -> dict:
    with SessionLocal() as session:
        auth = AuthService(session)
        user = auth.current_user(request)
        workspace = auth.current_workspace(user) if user else None
        return {"user": user, "workspace": workspace}


def _require_workspace(request: Request):
    with SessionLocal() as session:
        auth = AuthService(session)
        user = auth.current_user(request)
        if not user:
            return None, None
        workspace = auth.current_workspace(user)
        return user, workspace


def _github_status() -> dict:
    return {
        "connected": bool(settings.github_token),
        "login": None,
        "label": "Server token configured" if settings.github_token else "Not configured",
    }


def _slack_url() -> str:
    return f"{settings.app_base_url.rstrip('/')}/slack/events"


def _public_url(path: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}{path}"


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(
        request,
        "landing.html",
        {
            "request": request,
            "settings": settings,
            "github": _github_status(),
            **_auth_context(request),
        },
    )


@router.get("/auth/sign-up", response_class=HTMLResponse)
def sign_up_page(request: Request):
    return templates.TemplateResponse(
        request,
        "sign_up.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
            **_auth_context(request),
        },
    )


@router.post("/auth/sign-up")
def sign_up(
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    workspace_name: str = Form(...),
):
    with SessionLocal() as session:
        auth = AuthService(session)
        try:
            user = auth.create_user(email, name, password, workspace_name)
        except ValueError:
            return RedirectResponse("/auth/sign-up?error=existing_user", status_code=303)
        verification_link = _public_url(f"/auth/verify-email?token={user.email_verification_token}")
        response = RedirectResponse("/app", status_code=303)
        auth.login(response, user)
        response.set_cookie("syntra_last_verification_link", verification_link, max_age=600)
        return response


@router.get("/auth/sign-in", response_class=HTMLResponse)
def sign_in_page(request: Request):
    return templates.TemplateResponse(
        request, "sign_in.html", {"request": request, **_auth_context(request)}
    )


@router.post("/auth/sign-in")
def sign_in(email: str = Form(...), password: str = Form(...)):
    with SessionLocal() as session:
        auth = AuthService(session)
        user = auth.authenticate(email, password)
        if not user:
            return RedirectResponse("/auth/sign-in?error=1", status_code=303)
        response = RedirectResponse("/app", status_code=303)
        auth.login(response, user)
        response.delete_cookie("syntra_last_verification_link")
        return response


@router.post("/auth/logout")
def logout():
    with SessionLocal() as session:
        response = RedirectResponse("/", status_code=303)
        AuthService(session).logout(response)
        return response


@router.get("/auth/verify-email")
def verify_email(token: str):
    with SessionLocal() as session:
        AuthService(session).verify_email(token)
    return RedirectResponse("/app?verified=1", status_code=303)


@router.get("/auth/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request, "forgot_password.html", {"request": request, **_auth_context(request)}
    )


@router.post("/auth/forgot-password", response_class=HTMLResponse)
def forgot_password(request: Request, email: str = Form(...)):
    with SessionLocal() as session:
        user = AuthService(session).create_password_reset(email)
        reset_link = (
            _public_url(f"/auth/reset-password?token={user.password_reset_token}") if user else None
        )
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"request": request, "reset_link": reset_link, **_auth_context(request)},
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse(
        request, "reset_password.html", {"request": request, "token": token, **_auth_context(request)}
    )


@router.post("/auth/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...)):
    with SessionLocal() as session:
        AuthService(session).reset_password(token, password)
    return RedirectResponse("/auth/sign-in?reset=1", status_code=303)


@router.get("/app", response_class=HTMLResponse)
def dashboard(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        projects = session.scalars(
            select(Project)
            .where(Project.workspace_id == workspace.id)
            .order_by(Project.name)
        ).all()
        bugs = session.scalars(
            select(Bug)
            .where(Bug.workspace_id == workspace.id)
            .order_by(desc(Bug.created_at))
            .limit(8)
        ).all()
        jobs = session.scalars(
            select(Job)
            .join(Bug, Job.bug_id == Bug.bug_id)
            .where(Bug.workspace_id == workspace.id)
            .order_by(desc(Job.created_at))
            .limit(6)
        ).all()
        audits = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace.id)
            .order_by(desc(AuditEvent.created_at))
            .limit(8)
        ).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "projects": projects,
            "bugs": bugs,
            "jobs": jobs,
            "audits": audits,
            "github": _github_status(),
            "slack_url": _slack_url(),
            "llm_provider": settings.llm_provider,
            "user": user,
            "workspace": workspace,
            "verification_link": request.cookies.get("syntra_last_verification_link"),
        },
    )


@router.get("/app/projects", response_class=HTMLResponse)
def projects_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        projects = session.scalars(
            select(Project)
            .where(Project.workspace_id == workspace.id)
            .order_by(Project.name)
        ).all()
    return templates.TemplateResponse(
        request,
        "projects.html",
        {"request": request, "projects": projects, "user": user, "workspace": workspace},
    )


@router.post("/app/projects")
def create_project(
    request: Request,
    name: str = Form(...),
    repository_url: str = Form(...),
    default_branch: str = Form("main"),
):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        ProjectService(session).register(
            ProjectCreate(name=name, repository_url=repository_url, default_branch=default_branch),
            workspace_id=workspace.id,
        )
    return RedirectResponse("/app/projects", status_code=303)


@router.get("/app/bugs", response_class=HTMLResponse)
def bugs_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        bugs = session.scalars(
            select(Bug)
            .where(Bug.workspace_id == workspace.id)
            .order_by(desc(Bug.created_at))
        ).all()
    return templates.TemplateResponse(
        request, "bugs.html", {"request": request, "bugs": bugs, "user": user, "workspace": workspace}
    )


@router.get("/app/bugs/new", response_class=HTMLResponse)
def new_bug_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        projects = session.scalars(
            select(Project)
            .where(Project.workspace_id == workspace.id)
            .order_by(Project.name)
        ).all()
    return templates.TemplateResponse(
        request,
        "new_bug.html",
        {"request": request, "projects": projects, "user": user, "workspace": workspace},
    )


@router.post("/app/bugs")
def create_bug_from_web(
    request: Request,
    project_name: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    priority: str = Form("medium"),
):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        project = ProjectService(session).get_by_name(project_name, workspace.id)
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

    with SessionLocal() as session:
        JobService(session).enqueue_bug(bug_id)
    return RedirectResponse(f"/app/bugs?created={bug_id}", status_code=303)


@router.get("/app/github", response_class=HTMLResponse)
def github_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        installations = session.scalars(
            select(GitHubInstallation).where(GitHubInstallation.workspace_id == workspace.id)
        ).all()
    return templates.TemplateResponse(
        request,
        "github.html",
        {
            "request": request,
            "github": _github_status(),
            "installations": installations,
            "user": user,
            "workspace": workspace,
        },
    )


@router.post("/app/github/installations")
def save_github_installation(
    request: Request,
    installation_id: str = Form(""),
    account_login: str = Form(""),
    account_type: str = Form("Organization"),
):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        session.add(
            GitHubInstallation(
                workspace_id=workspace.id,
                installation_id=installation_id or None,
                account_login=account_login or None,
                account_type=account_type,
                status="configured",
            )
        )
        session.commit()
    return RedirectResponse("/app/github", status_code=303)


@router.get("/integrations/github/install")
def github_install(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        url = IntegrationService(session).github_install_url()
    if not url:
        return RedirectResponse("/app/github?missing_config=1", status_code=303)
    return RedirectResponse(url, status_code=303)


@router.get("/integrations/github/callback")
def github_callback(request: Request, installation_id: str = "", setup_action: str = "installed"):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    if installation_id:
        with SessionLocal() as session:
            IntegrationService(session).save_github_installation(
                workspace.id, installation_id, setup_action=setup_action
            )
    return RedirectResponse("/app/github", status_code=303)


@router.get("/app/slack", response_class=HTMLResponse)
def slack_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        installations = session.scalars(
            select(SlackInstallation).where(SlackInstallation.workspace_id == workspace.id)
        ).all()
    return templates.TemplateResponse(
        request,
        "slack.html",
        {
            "request": request,
            "slack_url": _slack_url(),
            "installations": installations,
            "slack_install_url": IntegrationService(session).slack_install_url(
                _public_url("/integrations/slack/callback")
            ),
            "user": user,
            "workspace": workspace,
        },
    )


@router.post("/app/slack/installations")
def save_slack_installation(
    request: Request,
    team_id: str = Form(""),
    team_name: str = Form(""),
    bot_user_id: str = Form(""),
):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        session.add(
            SlackInstallation(
                workspace_id=workspace.id,
                team_id=team_id or None,
                team_name=team_name or None,
                bot_user_id=bot_user_id or None,
                status="configured",
            )
        )
        session.commit()
    return RedirectResponse("/app/slack", status_code=303)


@router.get("/integrations/slack/install")
def slack_install(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        url = IntegrationService(session).slack_install_url(_public_url("/integrations/slack/callback"))
    if not url:
        return RedirectResponse("/app/slack?missing_config=1", status_code=303)
    return RedirectResponse(url, status_code=303)


@router.get("/integrations/slack/callback")
async def slack_callback(request: Request, code: str = ""):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    if code:
        with SessionLocal() as session:
            await IntegrationService(session).exchange_slack_code(
                code, _public_url("/integrations/slack/callback"), workspace.id
            )
    return RedirectResponse("/app/slack", status_code=303)


@router.get("/app/approvals", response_class=HTMLResponse)
def approvals_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        bugs = session.scalars(
            select(Bug)
            .where(
                Bug.status == BugStatus.PR_CREATED,
                Bug.workspace_id == workspace.id,
            )
            .order_by(desc(Bug.created_at))
        ).all()
    return templates.TemplateResponse(
        request,
        "approvals.html",
        {"request": request, "bugs": bugs, "user": user, "workspace": workspace},
    )


@router.post("/app/approvals/{bug_id}/approve")
def approve_bug(request: Request, bug_id: str):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        bugs = BugService(session)
        bug = bugs.get_for_workspace(bug_id, workspace.id)
        if not bug or not bug.pr_number:
            return RedirectResponse("/app/approvals?error=missing", status_code=303)
        GitHubService(settings.github_token).merge_pr(
            bug.project.repository_url,
            bug.pr_number,
            f"Merge Syntra fix for {bug.bug_id}",
        )
        bugs.mark_merged(bug)
    return RedirectResponse("/app/approvals", status_code=303)


@router.post("/app/approvals/{bug_id}/reject")
def reject_bug_from_web(request: Request, bug_id: str):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        bug = BugService(session).get_for_workspace(bug_id, workspace.id)
        if bug:
            BugService(session).mark_rejected(bug)
    return RedirectResponse("/app/approvals", status_code=303)


@router.get("/app/team", response_class=HTMLResponse)
def team_page(request: Request):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        workspace_ref = session.get(Workspace, workspace.id)
        members = list(workspace_ref.members) if workspace_ref else []
        for member in members:
            _ = member.user.email
        invitations = list(workspace_ref.invitations) if workspace_ref else []
    return templates.TemplateResponse(
        request,
        "team.html",
        {
            "request": request,
            "members": members,
            "invitations": invitations,
            "user": user,
            "workspace": workspace,
            "base_url": settings.app_base_url.rstrip(),
        },
    )


@router.post("/app/team/invitations")
def create_invitation(request: Request, email: str = Form(...), role: str = Form("MEMBER")):
    user, workspace = _require_workspace(request)
    if not user or not workspace:
        return RedirectResponse("/auth/sign-in", status_code=303)
    with SessionLocal() as session:
        InvitationService(session).create(workspace.id, email, MemberRole(role))
    return RedirectResponse("/app/team", status_code=303)


@router.get("/invite/{token}", response_class=HTMLResponse)
def accept_invitation_page(request: Request, token: str):
    return templates.TemplateResponse(
        request,
        "accept_invitation.html",
        {"request": request, "token": token, **_auth_context(request)},
    )


@router.post("/invite/{token}")
def accept_invitation(request: Request, token: str):
    user, workspace = _require_workspace(request)
    if not user:
        return RedirectResponse(f"/auth/sign-in?invite={token}", status_code=303)
    with SessionLocal() as session:
        auth = AuthService(session)
        session_user = auth.current_user(request)
        InvitationService(session).accept(token, session_user)
    return RedirectResponse("/app", status_code=303)
