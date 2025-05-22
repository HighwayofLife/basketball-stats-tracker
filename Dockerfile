FROM python:3.11-slim AS builder

WORKDIR /build

# Copy pyproject.toml for dependencies
COPY pyproject.toml ./

# Install build dependencies
RUN pip install --no-cache-dir build wheel setuptools

# Install runtime dependencies to collect them
RUN pip install --no-cache-dir ".[dev]" --target=/install

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages/

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
