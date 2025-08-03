# syntax=docker/dockerfile:1.4

# Choose a python version that you know works with your application
FROM python:3.11-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install the requirements using uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Copy application files
COPY civicsignal/ .

EXPOSE 8080

# Create a non-root user and switch to it
RUN useradd -m app_user
USER app_user

VOLUME [ "/app/civicsignal/cache" ]
VOLUME [ "/app/civicsignal/sf_meetings_rag_db" ]

CMD [ "marimo", "run", "civicsignal/app.py", "--host", "0.0.0.0", "-p", "8080" ]