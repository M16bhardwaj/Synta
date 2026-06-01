import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("GITHUB_TOKEN", "test")
os.environ.setdefault("SLACK_BOT_TOKEN", "test")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test")
os.environ.setdefault("SLACK_APP_TOKEN", "test")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("WORKSPACE_DIR", "./workspace-test")
