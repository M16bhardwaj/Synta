from sqlalchemy import select
from sqlalchemy.orm import Session

from syntra.db.models import Project
from syntra.schemas.projects import ProjectCreate


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def register(self, data: ProjectCreate) -> Project:
        existing = self.get_by_name(data.name)
        if existing:
            existing.repository_url = str(data.repository_url)
            existing.default_branch = data.default_branch
            self.session.commit()
            self.session.refresh(existing)
            return existing

        project = Project(
            name=data.name,
            repository_url=str(data.repository_url),
            default_branch=data.default_branch,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_name(self, name: str) -> Project | None:
        return self.session.scalar(select(Project).where(Project.name == name))
