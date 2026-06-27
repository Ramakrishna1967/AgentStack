# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""FastAPI application factory with lifespan management and CORS."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.db import get_database
from api.middleware import add_cors_middleware, rate_limit_middleware
from api.schemas import HealthResponse

logger = logging.getLogger("agentstack.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    from api.routes import ws

    # Startup
    logger.info("AgentStack API starting...")
    db = get_database()
    await db.init_db()
    logger.info("Database initialized successfully")
    
    # Start WS Consumer
    await ws.start_ws_consumer()

    yield

    # Shutdown
    await ws.stop_ws_consumer()
    logger.info("AgentStack API shutting down...")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AgentStack API",
        description="Chrome DevTools for AI Agents  Observability API",
        version="0.1.0-alpha",
        lifespan=lifespan,
    )

    # Add CORS middleware
    add_cors_middleware(app)

    # Add rate limiting middleware
    app.middleware("http")(rate_limit_middleware)

    # Root endpoint
    @app.get("/", tags=["system"])
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "AgentStack API",
            "version": "0.1.0-alpha",
            "docs": "/docs",
            "health": "/health",
        }

    # Import and include routers
    from api.routes import traces, spans, projects, security, analytics, auth, ws, health

    app.include_router(traces.router, prefix="/api/v1", tags=["traces"])
    app.include_router(spans.router, prefix="/api/v1", tags=["spans"])
    app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
    app.include_router(security.router, prefix="/api/v1", tags=["security"])
    app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(health.router, prefix="/api/v1", tags=["system"])
    app.include_router(ws.router, tags=["websocket"])

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
