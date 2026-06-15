# Syntra

Syntra is an AI software engineering assistant that turns bug reports into reviewed GitHub pull requests.

A user reports a bug from Slack or the web app. Syntra finds the registered project, analyzes the repository, plans a minimal fix, modifies code, runs validation, opens a pull request, and waits for explicit human approval before merge.

Syntra never merges automatically.

## What Syntra Does

- Accepts bug reports from Slack with `/syntra-fix`
- Accepts bug reports from the web dashboard
- Lets teams register GitHub repositories once as projects
- Clones the target repository and creates a bug-fix branch
- Uses an Agno-based agent workflow to analyze, plan, implement, validate, and prepare the PR
- Runs available validation commands such as tests, lint, build, or language-specific checks
- Creates a GitHub pull request with a structured summary
- Shows bug status, queued jobs, projects, integrations, and approvals in a web dashboard
- Requires human approval before merge

## Tech Stack

- **Backend:** Python 3.12, FastAPI
- **Agent framework:** Agno
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Validation:** Pydantic, Pytest
- **Slack:** Slack Bolt for Python
- **GitHub:** PyGithub
- **Git operations:** GitPython
- **LLM layer:** Centralized provider service with `openai` and `mock` modes
- **Deployment:** Docker, Docker Compose, Vercel for web/API
- **Package manager:** uv

## Architecture

Syntra is intentionally simple. It is not a microservice platform.

```text
Slack / Web
   |
FastAPI app
   |
PostgreSQL
   |
Job queue
   |
Worker with git installed
   |
Repository clone -> AI fix -> validation -> GitHub PR
   |
Human approval
   |
Merge
```

Main modules:

- `syntra/main.py` - FastAPI app, Slack routing, internal job endpoint
- `syntra/web/routes.py` - server-rendered web dashboard
- `syntra/worker.py` - background worker for queued bug-fix jobs
- `syntra/agents/` - intake, repository, planning, implementation, validation, and pull request agents
- `syntra/services/` - auth, Slack, GitHub, Git, jobs, projects, LLM, validation, integrations
- `syntra/db/models.py` - SQLAlchemy models
- `syntra/api/` - API routes
- `syntra/web/templates/` - Jinja templates
- `syntra/web/static/` - app styling

## Important Deployment Note

Vercel can host the web/API app.

The actual bug-fix worker needs a runtime with the `git` executable installed because Syntra clones repositories, creates branches, commits, pushes, and opens PRs. Use Render, Railway, Fly.io, ECS, or a similar worker-friendly host for `syntra-worker`.

## Environment Variables

Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

Required values:

```env
DATABASE_URL=your-postgres-connection-url
GITHUB_TOKEN=your-github-token

SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=your-slack-app-token

LLM_PROVIDER=mock
LLM_API_KEY=not-needed-for-mock

ENCRYPTION_KEY=your-generated-fernet-key
CRON_SECRET=your-random-cron-secret

AUTO_CREATE_DB=true
WORKSPACE_DIR=./workspace
APP_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

Optional GitHub App / Slack OAuth values:

```env
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_SLUG=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
```

Generate `ENCRYPTION_KEY`:

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use `LLM_PROVIDER=mock` for local testing without an OpenAI key. Use `LLM_PROVIDER=openai` with a real `LLM_API_KEY` when you want AI-generated code changes.

## Local Development

Install dependencies:

```powershell
uv sync --extra dev
```

Run migrations:

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

## Web Workflow

1. Create a workspace.
2. Register a project with a GitHub repository URL.
3. Configure GitHub and Slack integrations.
4. Submit a bug from `/app/bugs/new` or Slack.
5. Run the worker.
6. Review the created PR.
7. Approve or reject from the web approval page or Slack.

## Slack Workflow

Slack command:

```text
/syntra-fix project=crm-web title=Login button broken description=Clicking login does nothing priority=medium
```

For local Slack testing, expose the app:

```powershell
ngrok http 8000
```

Set Slack request URLs to:

```text
https://your-public-url/slack/events
```

Required Slack bot scopes:

- `commands`
- `chat:write`

Slack OAuth routes:

```text
/integrations/slack/install
/integrations/slack/callback
```

## GitHub Setup

For local demos, `GITHUB_TOKEN` is enough.

For hosted teams, configure a GitHub App:

```env
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_SLUG=
```

GitHub App routes:

```text
/integrations/github/install
/integrations/github/callback
```

## Vercel Deployment

See [VERCEL.md](VERCEL.md).

For Vercel:

```env
AUTO_CREATE_DB=false
WORKSPACE_DIR=/tmp/syntra-repos
APP_BASE_URL=https://your-vercel-domain.vercel.app
```

Run database migrations once against your hosted database:

```powershell
$env:DATABASE_URL="your-hosted-postgres-url"
uv run python -m syntra.db.migrate
```

## Tests

```powershell
uv run pytest
```

## Current Limitations

- The web/API can run on Vercel, but the worker must run somewhere with `git` installed.
- Email verification and password reset currently produce local/dev links; production email delivery is not wired yet.
- GitHub App installation-token usage is partially wired, but the local demo path still supports `GITHUB_TOKEN`.
- This is an MVP, not a full enterprise SaaS platform.

## Security Notes

- Never commit `.env`.
- Rotate any credentials that were shared in logs, screenshots, or chat.
- Keep `ENCRYPTION_KEY`, `CRON_SECRET`, GitHub, Slack, OpenAI, and database credentials in your deployment provider's environment-variable store.
