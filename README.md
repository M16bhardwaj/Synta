# Syntra

Syntra is an autonomous software engineering assistant for the bug-fix loop. A user reports a bug, Syntra finds the registered GitHub repository, creates a branch, makes a minimal fix, runs validation, opens a pull request, and waits for explicit human approval before merge.

The original MVP was Slack-only. The current build is a focused product foundation with authentication, workspaces, GitHub/Slack installation flows, a web dashboard, a worker process, team invites, and approval UI.

Human approval is mandatory. Syntra never merges automatically.

## What Works Now

- User sign-up and sign-in
- Session cookies
- Email verification token flow
- Password reset token flow
- Workspace creation
- Team invitations
- Project registration
- Slack `/syntra-fix` intake
- Web bug submission
- Repository clone, branch, commit, push
- PR creation and merge after approval
- Web approval center
- GitHub App installation redirect and callback wiring
- Slack OAuth install and callback wiring
- Encrypted installation token storage
- PostgreSQL-backed job queue
- Separate worker process
- Mock LLM mode for testing without an OpenAI key

## Architecture

- `syntra/main.py`: FastAPI app and Slack event routing
- `syntra/web/routes.py`: server-rendered web app and SaaS flows
- `syntra/worker.py`: background job worker
- `syntra/db/models.py`: users, workspaces, projects, bugs, jobs, installations, invitations, audit events
- `syntra/services/auth.py`: signup, login, verification, password reset
- `syntra/services/integrations.py`: GitHub App and Slack OAuth flows
- `syntra/services/git_service.py`: clone, branch, commit, push
- `syntra/services/github_service.py`: PR creation, merge, GitHub App installation token helper
- `syntra/services/slack.py`: Slack command and approval actions
- `syntra/services/llm.py`: centralized LLM service with `openai` and `mock` providers
- `syntra/agents/*`: intake, repository, planning, implementation, validation, pull request agents

## Environment

Copy `.env.example` to `.env` and fill in:

```env
DATABASE_URL=postgresql+psycopg://syntra:syntra@postgres:5432/syntra
GITHUB_TOKEN=...
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=...
LLM_PROVIDER=mock
LLM_API_KEY=not-needed-for-mock
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_SLUG=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
ENCRYPTION_KEY=
AUTO_CREATE_DB=true
WORKSPACE_DIR=/workspace/repos
APP_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

Generate `ENCRYPTION_KEY`:

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use `LLM_PROVIDER=mock` while testing without an OpenAI key. Switch to `LLM_PROVIDER=openai` when you have a real key.

## Local Run

Install dependencies:

```powershell
uv sync --extra dev
```

Apply schema migrations:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\migrate.ps1
```

Start the web app:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

Start the worker in a second terminal:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-worker.ps1
```

Open:

```text
http://localhost:8000
```

## Docker

```powershell
docker compose up --build
```

Docker Compose starts:

- `app`
- `worker`
- `postgres`

## Vercel

See [VERCEL.md](VERCEL.md).

Vercel can host the web/API app. For demos, Vercel Cron can call `/internal/jobs/run-once` to process queued jobs. For production, run `syntra-worker` on a worker-friendly host such as Render, Railway, Fly.io, or ECS.

## Slack Setup

Expose the app locally:

```powershell
ngrok http 8000
```

Set both Slack URLs to:

```text
https://your-public-url/slack/events
```

Required bot scopes:

- `commands`
- `chat:write`

Slack OAuth is wired at:

```text
/integrations/slack/install
/integrations/slack/callback
```

Configure `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` to use the Add-to-Slack flow.

## GitHub App

GitHub App installation is wired at:

```text
/integrations/github/install
/integrations/github/callback
```

Configure:

```env
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_SLUG=
```

The callback stores `installation_id`. `GitHubService.installation_token()` can mint installation tokens when app credentials are configured. The app can still use `GITHUB_TOKEN` for local demos.

## Web Workflow

1. Create a workspace.
2. Verify email using the local development link shown in the dashboard.
3. Register a project.
4. Connect or record GitHub/Slack installations.
5. Submit a bug from `/app/bugs/new`.
6. Run the worker.
7. Review status in `/app/bugs`.
8. Approve PRs from `/app/approvals`.

## Tests

```powershell
uv run pytest
```

## Remaining Production Work

- Add SMTP or a transactional email provider for real verification/reset delivery.
- Use GitHub App installation tokens throughout clone/push/PR paths per workspace.
- Add Alembic revisioned migrations if you want production-grade schema history.
