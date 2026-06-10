from syntra.core.config import get_settings
from syntra.core.logging import configure_logging
from syntra.db.base import create_db


def run_migrations() -> None:
    configure_logging(get_settings())
    create_db()
    print("Syntra database migrations applied.")


if __name__ == "__main__":
    run_migrations()
