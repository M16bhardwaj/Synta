from sqlalchemy import select
from sqlalchemy.orm import Session

from syntra.db.models import Project
from syntra.schemas.projects import ProjectCreate


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def register(self, data: ProjectCreate, workspace_id: int | None = None) -> Project:
        existing = self.get_by_name(data.name, workspace_id)
        if existing:
            existing.repository_url = str(data.repository_url)
            existing.default_branch = data.default_branch
            existing.workspace_id = workspace_id or existing.workspace_id
            self.session.commit()
            self.session.refresh(existing)
            return existing

        project = Project(
            workspace_id=workspace_id,
            name=data.name,
            repository_url=str(data.repository_url),
            default_branch=data.default_branch,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_name(self, name: str, workspace_id: int | None = None) -> Project | None:
        query = select(Project).where(Project.name == name)
        if workspace_id is not None:
            query = query.where(
                (Project.workspace_id == workspace_id) | (Project.workspace_id.is_(None))
            )
        return self.session.scalar(query)
