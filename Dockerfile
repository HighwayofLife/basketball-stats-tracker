# Base stage with common setup
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and app structure
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./
COPY app ./app

# Development stage
FROM base AS development

# Install all dependencies including dev
RUN pip install --no-cache-dir -e ".[dev]"

# Don't copy files in development - we'll use volume mount instead
# COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use uvicorn with reload for development
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--reload"]

# Production stage
FROM base AS production

# Accept build arguments for version info
ARG APP_VERSION=0.4.3
ARG GIT_HASH=unknown

# Install only runtime dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Create version info file
RUN echo "{\"version\": \"$APP_VERSION\", \"git_hash\": \"$GIT_HASH\", \"full_version\": \"v$APP_VERSION-$GIT_HASH\"}" > /app/app/VERSION.json

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use uvicorn directly for better performance
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
