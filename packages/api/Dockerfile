FROM node:20-alpine AS dashboard-builder

WORKDIR /dashboard

COPY packages/dashboard/package.json packages/dashboard/package-lock.json* ./
RUN npm install

COPY packages/dashboard/. .
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# LOW-4 FIX: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Install build tools
RUN pip install --no-cache-dir hatch

# Copy package files
COPY packages/api/pyproject.toml packages/api/README.md ./
COPY packages/api/src ./src

# Install dependencies
RUN pip install --no-cache-dir .

# Dashboard's built dist/, served by main.py's StaticFiles mount + SPA fallback
COPY --from=dashboard-builder /dashboard/dist ./src/api/static

# Create data directory with correct permissions
RUN mkdir -p /data && chown -R appuser:appuser /data /app

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Default command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
