from pydantic import BaseModel, Field


class BugIntake(BaseModel):
    project: str
    title: str
    description: str
    priority: str = Field(default="medium")


class BugResponse(BaseModel):
    bug_id: str
    status: str
    pr_url: str | None = None
    validation_result: str | None = None
