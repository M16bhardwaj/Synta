from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from syntra.db.base import get_session
from syntra.schemas.projects import ProjectCreate, ProjectRead
from syntra.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead)
def register_project(payload: ProjectCreate, session: Session = Depends(get_session)):
    return ProjectService(session).register(payload)
