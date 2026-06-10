import asyncio
import logging
import time

from syntra.core.config import get_settings
from syntra.core.logging import configure_logging
from syntra.db.base import SessionLocal, create_db
from syntra.services.job_runner import run_queued_job_once

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


async def run_job_once() -> bool:
    with SessionLocal() as session:
        result = await run_queued_job_once(session)
        return bool(result.get("processed"))


def run_worker() -> None:
    create_db()
    logger.info("Syntra worker started")
    while True:
        did_work = asyncio.run(run_job_once())
        if not did_work:
            time.sleep(3)


if __name__ == "__main__":
    run_worker()
