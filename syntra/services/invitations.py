import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from syntra.db.models import Invitation, InvitationStatus, MemberRole, User, WorkspaceMember


class InvitationService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, workspace_id: int, email: str, role: MemberRole = MemberRole.MEMBER) -> Invitation:
        invitation = Invitation(
            workspace_id=workspace_id,
            email=email.lower(),
            role=role,
            token=secrets.token_urlsafe(32),
        )
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        return invitation

    def accept(self, token: str, user: User) -> Invitation:
        invitation = self.session.scalar(select(Invitation).where(Invitation.token == token))
        if not invitation or invitation.status != InvitationStatus.PENDING:
            raise ValueError("Invitation is not valid.")
        existing = self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == invitation.workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        if not existing:
            self.session.add(
                WorkspaceMember(
                    workspace_id=invitation.workspace_id,
                    user_id=user.id,
                    role=invitation.role,
                )
            )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(invitation)
        return invitation
