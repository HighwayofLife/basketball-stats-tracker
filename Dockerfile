FROM python:3.11-slim AS builder

WORKDIR /build

# Copy pyproject.toml and source code for dependencies
COPY pyproject.toml ./
COPY app ./app
COPY README.md ./
COPY LICENSE ./

# Install build dependencies and the package
RUN pip install --no-cache-dir build wheel setuptools && \
    pip install --no-cache-dir ".[dev]"

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY pyproject.toml ./
COPY app ./app
COPY README.md ./
COPY LICENSE ./

RUN pip install --no-cache-dir . && \
    pip cache purge

# Copy application code
COPY . .

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
CMD ["uvicorn", "app.web_ui:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
