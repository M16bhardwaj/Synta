# Deploy Syntra on Vercel

Syntra can be deployed to Vercel as a FastAPI application. The repo exposes the app through root `app.py`:

```python
from syntra.main import app
```

## Important Architecture Note

Vercel is serverless. It is good for the web app, Slack endpoints, GitHub callbacks, and lightweight API requests.

Syntra's heavy workflow does repository cloning, code modification, validation, Git push, and PR creation. Vercel's Python runtime does not provide the `git` executable that GitPython needs, so the worker should run on a host with git installed.

The cron endpoint remains available for worker-style hosts or future queue triggers:

```text
/internal/jobs/run-once
```

For real bug-fix jobs, run `syntra-worker` on Render, Railway, Fly.io, ECS, or another runtime that supports long-lived background processes and has git installed.

## Required Hosted Services

Do not use your local PostgreSQL for Vercel. Use a hosted Postgres database such as:

- Vercel Postgres / Neon
- Supabase Postgres
- Railway Postgres
- Render Postgres

Set `DATABASE_URL` to the hosted database URL.

For file writes, use:

```env
WORKSPACE_DIR=/tmp/syntra-repos
```

Vercel functions can write to `/tmp`, but it is ephemeral.

## Environment Variables

Add these in Vercel Project Settings:

```env
DATABASE_URL=
GITHUB_TOKEN=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APP_TOKEN=
LLM_PROVIDER=mock
LLM_API_KEY=not-needed-for-mock
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_SLUG=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
ENCRYPTION_KEY=
CRON_SECRET=
AUTO_CREATE_DB=false
WORKSPACE_DIR=/tmp/syntra-repos
APP_BASE_URL=https://your-vercel-domain.vercel.app
LOG_LEVEL=INFO
```

Generate `ENCRYPTION_KEY` locally:

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate `CRON_SECRET` as a random password with at least 16 characters.

## Deploy From GitHub

1. Push this repo to GitHub.
2. Go to Vercel.
3. Click **Add New Project**.
4. Import the `syntra` repository.
5. Add all environment variables above.
6. Deploy.

Vercel will install Python dependencies from `pyproject.toml`.

## Run Migrations

After the first deploy, run migrations once from your local machine against the hosted database:

```powershell
$env:DATABASE_URL="your-hosted-database-url"
uv run python -m syntra.db.migrate
```

Or use Vercel's project shell/logged command support if available for your account.

## Configure Slack

Set Slack URLs to:

```text
https://your-vercel-domain.vercel.app/slack/events
```

Use that URL for:

- Slash command `/syntra-fix`
- Interactivity & Shortcuts

## Configure GitHub App

Set the GitHub App callback URL to:

```text
https://your-vercel-domain.vercel.app/integrations/github/callback
```

## Configure Slack OAuth

Set the Slack OAuth redirect URL to:

```text
https://your-vercel-domain.vercel.app/integrations/slack/callback
```

## Cron Jobs

`vercel.json` defines:

```json
{
  "path": "/internal/jobs/run-once",
  "schedule": "0 0 * * *"
}
```

Vercel sends `CRON_SECRET` as a bearer token in the `Authorization` header when configured in the environment.

## Recommended Production Split

For real users:

- Deploy web/API to Vercel.
- Deploy `syntra-worker` to Railway/Render/Fly.
- Use the same hosted Postgres database.
- Keep `WORKSPACE_DIR` on the worker as persistent disk if possible.
