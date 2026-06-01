FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

COPY pyproject.toml README.md ./
COPY syntra ./syntra

RUN uv pip install --system -e .

CMD ["uvicorn", "syntra.main:app", "--host", "0.0.0.0", "--port", "8000"]
