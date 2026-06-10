from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from syntra.core.config import get_settings
from syntra.db.models import GitHubInstallation, SlackInstallation
from syntra.services.secrets import SecretBox


class IntegrationService:
    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()
        self.secrets = SecretBox()

    def github_install_url(self) -> str | None:
        if not self.settings.github_app_slug:
            return None
        return f"https://github.com/apps/{self.settings.github_app_slug}/installations/new"

    def save_github_installation(
        self,
        workspace_id: int,
        installation_id: str,
        account_login: str | None = None,
        setup_action: str | None = None,
    ) -> GitHubInstallation:
        installation = GitHubInstallation(
            workspace_id=workspace_id,
            installation_id=installation_id,
            account_login=account_login,
            account_type="Organization",
            status=setup_action or "installed",
        )
        self.session.add(installation)
        self.session.commit()
        self.session.refresh(installation)
        return installation

    def slack_install_url(self, redirect_uri: str) -> str | None:
        if not self.settings.slack_client_id:
            return None
        params = urlencode(
            {
                "client_id": self.settings.slack_client_id,
                "scope": "commands,chat:write",
                "redirect_uri": redirect_uri,
            }
        )
        return f"https://slack.com/oauth/v2/authorize?{params}"

    async def exchange_slack_code(self, code: str, redirect_uri: str, workspace_id: int) -> SlackInstallation:
        if not self.settings.slack_client_id or not self.settings.slack_client_secret:
            raise ValueError("Slack OAuth credentials are not configured.")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.settings.slack_client_id,
                    "client_secret": self.settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
        payload = response.json()
        if not payload.get("ok"):
            raise ValueError(payload.get("error", "Slack OAuth failed."))
        installation = SlackInstallation(
            workspace_id=workspace_id,
            team_id=payload.get("team", {}).get("id"),
            team_name=payload.get("team", {}).get("name"),
            bot_user_id=payload.get("bot_user_id"),
            encrypted_bot_token=self.secrets.encrypt(payload.get("access_token")),
            encrypted_access_token=self.secrets.encrypt(payload.get("authed_user", {}).get("access_token")),
            status="installed",
        )
        self.session.add(installation)
        self.session.commit()
        self.session.refresh(installation)
        return installation
