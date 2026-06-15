from fastapi import APIRouter, HTTPException

from syntra.schemas.projects import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("")
def register_project(payload: ProjectCreate):
    raise HTTPException(
        status_code=410,
        detail="Use /app/projects after signing in so the project is scoped to a workspace.",
    )
