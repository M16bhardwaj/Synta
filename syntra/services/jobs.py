from sqlalchemy import select
from sqlalchemy.orm import Session

from syntra.db.models import Job, JobStatus


class JobService:
    def __init__(self, session: Session):
        self.session = session

    def enqueue_bug(self, bug_id: str) -> Job:
        existing = self.session.scalar(
            select(Job).where(Job.bug_id == bug_id, Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        )
        if existing:
            return existing
        job = Job(bug_id=bug_id, status=JobStatus.QUEUED)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def next_job(self) -> Job | None:
        job = self.session.scalar(
            select(Job).where(Job.status == JobStatus.QUEUED).order_by(Job.created_at).limit(1)
        )
        if not job:
            return None
        job.status = JobStatus.RUNNING
        job.attempts += 1
        self.session.commit()
        self.session.refresh(job)
        return job

    def complete(self, job: Job) -> None:
        job.status = JobStatus.COMPLETED
        self.session.commit()

    def fail(self, job: Job, message: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = message
        self.session.commit()
