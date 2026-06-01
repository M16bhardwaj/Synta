import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from syntra.db.base import Base


class BugStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    PR_CREATED = "PR_CREATED"
    MERGED = "MERGED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ValidationStatus(str, enum.Enum):
    PASSED = "PASSED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    repository_url: Mapped[str] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bugs: Mapped[list["Bug"]] = relationship(back_populates="project")


class Bug(Base):
    __tablename__ = "bugs"

    bug_id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: f"BUG-{uuid.uuid4().hex[:8].upper()}"
    )
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    status: Mapped[BugStatus] = mapped_column(Enum(BugStatus), default=BugStatus.RECEIVED)
    branch_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(nullable=True)
    validation_result: Mapped[ValidationStatus | None] = mapped_column(
        Enum(ValidationStatus), nullable=True
    )
    validation_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="bugs")
