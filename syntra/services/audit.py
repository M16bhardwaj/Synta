from sqlalchemy.orm import Session

from syntra.db.models import AuditEvent


class AuditService:
    def __init__(self, session: Session):
        self.session = session

    def record(
        self,
        action: str,
        subject: str,
        workspace_id: int | None = None,
        actor: str = "system",
        details: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            subject=subject,
            details=details,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
