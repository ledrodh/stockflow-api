# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml README.md ./
COPY src ./src

RUN poetry install --only main --no-ansi

# ==============================================================================
# Stage 2: Production Runtime
# ==============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1001 stockflow && \
    useradd --uid 1001 --gid stockflow --shell /bin/bash --create-home stockflow

COPY --from=builder --chown=stockflow:stockflow /app/.venv /app/.venv
COPY --chown=stockflow:stockflow src ./src
COPY --chown=stockflow:stockflow alembic.ini ./alembic.ini

USER stockflow

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn stockflow.main:app --host 0.0.0.0 --port 8000"]
