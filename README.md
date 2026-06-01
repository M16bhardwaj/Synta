# Syntra

Syntra is an MVP autonomous software engineering assistant. A user reports a bug from Slack, Syntra looks up the registered GitHub repository, creates a branch, makes a minimal code fix, runs validation, opens a pull request, and waits for explicit Slack approval before merging.

This is intentionally not a SaaS platform. There is no dashboard, tenant model, vector database, queue, Kubernetes deployment, telemetry stack, or autonomous feature-development loop.

## MVP Scope

Syntra proves one workflow:

1. Register a project once.
2. Submit a bug with `/syntra-fix` in Slack.
3. Syntra clones the repo and creates a `bugfix/...` branch.
4. Syntra analyzes the repo, plans a fix, and modifies code.
5. Syntra runs available validations.
6. Syntra opens a GitHub pull request.
7. Syntra posts the PR to Slack with `Approve Merge` and `Reject` buttons.
8. A human approves from Slack.
9. Syntra merges the PR.

Human approval is mandatory. Syntra never merges automatically.

## Architecture

- `syntra/main.py`: FastAPI app and workflow composition
- `syntra/services/slack.py`: Slack slash command and approval actions
- `syntra/db/models.py`: PostgreSQL tables for projects and bugs
- `syntra/services/git_service.py`: clone, branch, commit, push
- `syntra/services/github_service.py`: PR creation and merge
- `syntra/services/repository.py`: repository marker detection and candidate file lookup
- `syntra/services/validation.py`: validation command runner
- `syntra/services/llm.py`: centralized LLM service
- `syntra/agents/*`: six thin agents for intake, repository analysis, planning, implementation, validation, and PR creation

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
DATABASE_URL=postgresql+psycopg://syntra:syntra@postgres:5432/syntra
GITHUB_TOKEN=...
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=...
LLM_PROVIDER=openai
LLM_API_KEY=...
WORKSPACE_DIR=/workspace/repos
APP_BASE_URL=http://localhost:8000
```

## Local Setup

Install dependencies locally:

```bash
uv sync --extra dev
```

Run with Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

The API runs on `http://localhost:8000`.

## Project Registration

Register a project once:

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "crm-web",
    "repository_url": "https://github.com/company/crm-web",
    "default_branch": "main"
  }'
```

Users reference only the project name in Slack:

```text
project=crm-web
```

## Slack App Setup

Create a Slack app and enable:

- Slash command: `/syntra-fix`
- Request URL: `https://your-public-url/slack/events`
- Interactivity request URL: `https://your-public-url/slack/events`
- Bot token scopes: `commands`, `chat:write`

For local development, expose FastAPI through a tunnel such as ngrok:

```bash
ngrok http 8000
```

Install the app into your workspace and copy the bot token and signing secret into `.env`.

## GitHub Token Setup

Create a GitHub token with access to the target repositories. For private repositories, the token must be able to clone, push branches, create pull requests, and merge pull requests.

## Submit A Bug

In Slack:

```text
/syntra-fix
project=crm-web
title=Login button broken
description=Clicking login does nothing
priority=medium
```

Syntra replies when work begins:

```text
Syntra started working on BUG-123.
```

When a PR is ready, Syntra posts the bug ID, project, PR URL, validation status, summary, and buttons for `Approve Merge` or `Reject`.

## Approval

Click `Approve Merge` to merge the associated PR. Syntra verifies the bug and PR record, calls GitHub to merge, updates the bug status, and posts a confirmation.

Click `Reject` to mark the bug rejected. Syntra does not merge.

## Validation

Syntra runs available commands based on repository markers:

- Node: `npm test`, `npm run lint`, `npm run build`
- Python: `pytest`
- Java Maven: `mvn test`
- Java Gradle: `gradle test`
- Go: `go test ./...`

Validation status is:

- `PASSED`: all available validations succeeded
- `PARTIAL`: some commands were unavailable or no known commands were found
- `FAILED`: at least one available command failed

## Tests

```bash
uv run pytest
```

## Current Limitations

- One FastAPI process handles requests and background work.
- No durable job queue; failed process restarts do not resume active work.
- Repository understanding is marker and keyword based.
- Implementation depends on the centralized LLM service returning full replacement file contents.
- Slack uses HTTP request URLs; `SLACK_APP_TOKEN` is reserved for future Socket Mode support.
- Database migrations are not included; tables are created at startup for MVP speed.
