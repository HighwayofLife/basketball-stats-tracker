# Base image with common system setup
FROM python:3.11-slim AS base

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency descriptors only
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./

# Provide a minimal package structure so pip can resolve dependencies
RUN mkdir app && touch app/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf app

# Development stage ------------------------------------------------------
FROM base AS development

# Install additional development dependencies
RUN pip install --no-cache-dir .[dev]

# Copy application code and install in editable mode without deps
COPY . .
RUN pip install --no-cache-dir --no-deps -e .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--reload"]

# Production stage ------------------------------------------------------
FROM base AS production

ARG APP_VERSION
ARG GIT_HASH=unknown

# Copy application code
COPY . .

# Install package without reinstalling dependencies
RUN pip install --no-cache-dir --no-deps .

# Write version information
RUN echo "{\"version\": \"$APP_VERSION\", \"git_hash\": \"$GIT_HASH\", \"full_version\": \"v$APP_VERSION-$GIT_HASH\"}" > /app/app/VERSION.json

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
