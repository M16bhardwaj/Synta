from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from syntra.core.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_db() -> None:
    import syntra.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_legacy_columns()


def ensure_legacy_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        if "projects" in inspector.get_table_names():
            project_columns = {column["name"] for column in inspector.get_columns("projects")}
            if "workspace_id" not in project_columns:
                connection.execute(text("ALTER TABLE projects ADD COLUMN workspace_id INTEGER NULL"))
        if "bugs" in inspector.get_table_names():
            bug_columns = {column["name"] for column in inspector.get_columns("bugs")}
            if "workspace_id" not in bug_columns:
                connection.execute(text("ALTER TABLE bugs ADD COLUMN workspace_id INTEGER NULL"))
        if "users" in inspector.get_table_names():
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "email_verified" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
                )
            if "email_verification_token" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(160) NULL")
                )
            if "password_reset_token" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(160) NULL")
                )
            if "password_reset_expires_at" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMPTZ NULL")
                )
        if "workspaces" in inspector.get_table_names():
            workspace_columns = {column["name"] for column in inspector.get_columns("workspaces")}
            if "plan" not in workspace_columns:
                connection.execute(
                    text("ALTER TABLE workspaces ADD COLUMN plan VARCHAR(80) DEFAULT 'free'")
                )
            if "stripe_customer_id" not in workspace_columns:
                connection.execute(
                    text("ALTER TABLE workspaces ADD COLUMN stripe_customer_id VARCHAR(180) NULL")
                )
        if "github_installations" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("github_installations")}
            if "encrypted_access_token" not in columns:
                connection.execute(
                    text("ALTER TABLE github_installations ADD COLUMN encrypted_access_token TEXT NULL")
                )
        if "slack_installations" in inspector.get_table_names():
            columns = {column["name"] for column in inspector.get_columns("slack_installations")}
            if "encrypted_bot_token" not in columns:
                connection.execute(
                    text("ALTER TABLE slack_installations ADD COLUMN encrypted_bot_token TEXT NULL")
                )
            if "encrypted_access_token" not in columns:
                connection.execute(
                    text("ALTER TABLE slack_installations ADD COLUMN encrypted_access_token TEXT NULL")
                )


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
