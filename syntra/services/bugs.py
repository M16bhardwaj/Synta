from sqlalchemy.orm import Session
from sqlalchemy import select

from syntra.db.models import Bug, BugStatus, Project, ValidationStatus
from syntra.schemas.bugs import BugIntake


class BugService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project: Project, data: BugIntake) -> Bug:
        bug = Bug(
            project_id=project.id,
            workspace_id=project.workspace_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=BugStatus.RECEIVED,
        )
        self.session.add(bug)
        self.session.commit()
        self.session.refresh(bug)
        return bug

    def get(self, bug_id: str) -> Bug | None:
        return self.session.get(Bug, bug_id)

    def get_for_workspace(self, bug_id: str, workspace_id: int) -> Bug | None:
        return self.session.scalar(
            select(Bug).where(Bug.bug_id == bug_id, Bug.workspace_id == workspace_id)
        )

    def mark_started(self, bug: Bug) -> None:
        bug.status = BugStatus.IN_PROGRESS
        self.session.commit()

    def mark_pr_created(
        self,
        bug: Bug,
        branch_name: str,
        pr_url: str,
        pr_number: int,
        validation: ValidationStatus,
        validation_output: str,
    ) -> None:
        bug.status = BugStatus.PR_CREATED
        bug.branch_name = branch_name
        bug.pr_url = pr_url
        bug.pr_number = pr_number
        bug.validation_result = validation
        bug.validation_output = validation_output
        self.session.commit()

    def mark_failed(self, bug: Bug, message: str) -> None:
        bug.status = BugStatus.FAILED
        bug.error_message = message
        self.session.commit()

    def mark_merged(self, bug: Bug) -> None:
        bug.status = BugStatus.MERGED
        self.session.commit()

    def mark_rejected(self, bug: Bug) -> None:
        bug.status = BugStatus.REJECTED
        self.session.commit()
