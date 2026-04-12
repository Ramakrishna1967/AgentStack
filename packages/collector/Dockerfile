FROM python:3.11-slim

WORKDIR /app

# LOW-4 FIX: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Install build tools
RUN pip install --no-cache-dir hatch

# Copy package files
COPY packages/collector/pyproject.toml packages/collector/README.md ./
COPY packages/collector/src ./src

# Copy the API source for shared DB/auth imports
COPY packages/api/src/api /app/api_shared/api
ENV PYTHONPATH="/app/api_shared:${PYTHONPATH}"

# Install dependencies
RUN pip install --no-cache-dir .

# Create data directory with correct permissions
RUN mkdir -p /data && chown -R appuser:appuser /data /app

# Switch to non-root user
USER appuser

# Expose collector port
EXPOSE 4318

# Default command
CMD ["uvicorn", "collector.server:app", "--host", "0.0.0.0", "--port", "4318"]
