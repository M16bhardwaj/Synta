import logging

from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_sdk import WebClient
from sqlalchemy.orm import Session

from syntra.agents.intake import IntakeAgent
from syntra.core.config import Settings
from syntra.db.models import BugStatus
from syntra.services.bugs import BugService
from syntra.services.github_service import GitHubService
from syntra.services.projects import ProjectService

logger = logging.getLogger(__name__)


class SlackNotifier:
    def __init__(self, client: WebClient):
        self.client = client

    def started(self, channel: str, bug_id: str) -> None:
        self.client.chat_postMessage(channel=channel, text=f"Syntra started working on {bug_id}.")

    def pr_created(
        self,
        channel: str,
        bug_id: str,
        project_name: str,
        pr_url: str,
        validation_status: str,
        summary: str,
    ) -> None:
        self.client.chat_postMessage(
            channel=channel,
            text=f"Bug fix completed for {bug_id}: {pr_url}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Bug fix completed.*\n"
                            f"*Bug ID:* {bug_id}\n"
                            f"*Project:* {project_name}\n"
                            f"*PR:* {pr_url}\n"
                            f"*Validation:* {validation_status}\n"
                            f"*Summary:* {summary}"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve Merge"},
                            "style": "primary",
                            "action_id": "approve_merge",
                            "value": bug_id,
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject"},
                            "style": "danger",
                            "action_id": "reject_bug",
                            "value": bug_id,
                        },
                    ],
                },
            ],
        )

    def failed(self, channel: str, bug_id: str, message: str) -> None:
        self.client.chat_postMessage(
            channel=channel,
            text=f"Syntra failed while working on {bug_id}: {message}",
        )

    def merged(self, channel: str, bug_id: str, pr_url: str) -> None:
        self.client.chat_postMessage(channel=channel, text=f"{bug_id} merged successfully: {pr_url}")

    def rejected(self, channel: str, bug_id: str) -> None:
        self.client.chat_postMessage(channel=channel, text=f"{bug_id} rejected. PR was not merged.")


def create_slack_app(
    settings: Settings,
    enqueue_bug,
    session_factory,
    github_service: GitHubService,
) -> tuple[App, SlackRequestHandler]:
    app = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
        token_verification_enabled=False,
    )
    intake = IntakeAgent()

    @app.command("/syntra-fix")
    def syntra_fix(ack, body, client, respond):
        ack()
        channel = body["channel_id"]
        try:
            bug_data = intake.parse(body.get("text", ""))
            with session_factory() as session:
                project = ProjectService(session).get_by_name(bug_data.project)
                if not project:
                    respond(f"Unknown project `{bug_data.project}`. Register it before filing bugs.")
                    return
                bug = BugService(session).create(project, bug_data)
                bug_id = bug.bug_id
            respond(f"Syntra started working on {bug_id}.")
            enqueue_bug(bug_id, channel)
        except Exception as exc:
            logger.exception("Failed to accept Slack command")
            respond(f"Could not start Syntra: {exc}")

    @app.action("approve_merge")
    def approve_merge(ack, body, client):
        ack()
        bug_id = body["actions"][0]["value"]
        channel = body["channel"]["id"]
        notifier = SlackNotifier(client)
        with session_factory() as session:
            bugs = BugService(session)
            bug = bugs.get(bug_id)
            if not bug or not bug.pr_number or not bug.pr_url:
                notifier.failed(channel, bug_id, "Associated PR was not found.")
                return
            if bug.status != BugStatus.PR_CREATED:
                notifier.failed(channel, bug_id, f"Bug is not ready to merge. Current status: {bug.status}")
                return
            try:
                github_service.merge_pr(
                    bug.project.repository_url,
                    bug.pr_number,
                    f"Merge Syntra fix for {bug.bug_id}",
                )
                bugs.mark_merged(bug)
                notifier.merged(channel, bug.bug_id, bug.pr_url)
            except Exception as exc:
                bugs.mark_failed(bug, str(exc))
                notifier.failed(channel, bug_id, str(exc))

    @app.action("reject_bug")
    def reject_bug(ack, body, client):
        ack()
        bug_id = body["actions"][0]["value"]
        channel = body["channel"]["id"]
        with session_factory() as session:
            bug = BugService(session).get(bug_id)
            if bug:
                BugService(session).mark_rejected(bug)
        SlackNotifier(client).rejected(channel, bug_id)

    return app, SlackRequestHandler(app)
