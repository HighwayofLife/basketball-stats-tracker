# Base stage for dependency installation
FROM python:3.11-slim AS dependencies

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only files needed for pip install
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./

# Create minimal app structure and install all dependencies at once
RUN mkdir -p app && touch app/__init__.py

# Development stage
FROM dependencies AS development

# Install all dependencies including dev
RUN pip install --no-cache-dir -e ".[dev]"

# Install playwright browsers for UI testing
RUN playwright install --with-deps chromium

# Copy all application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security and ensure uploads directory exists
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use uvicorn with reload for development
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--reload"]

# Production stage
FROM dependencies AS production

# Accept build arguments for version info
ARG APP_VERSION
ARG GIT_HASH=unknown

# Install runtime dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Create version info file
RUN echo "{\"version\": \"$APP_VERSION\", \"git_hash\": \"$GIT_HASH\", \"full_version\": \"v$APP_VERSION-$GIT_HASH\"}" > /app/app/VERSION.json

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security and ensure uploads directory exists
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use uvicorn directly for better performance
CMD ["uvicorn", "app.web_ui.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
