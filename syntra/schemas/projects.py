from pydantic import BaseModel, HttpUrl


class ProjectCreate(BaseModel):
    name: str
    repository_url: HttpUrl
    default_branch: str = "main"


class ProjectRead(BaseModel):
    id: int
    name: str
    repository_url: str
    default_branch: str

    model_config = {"from_attributes": True}
