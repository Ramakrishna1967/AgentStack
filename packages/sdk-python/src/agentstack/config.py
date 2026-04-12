# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""AgentStack SDK configuration loaded from environment variables.

All configuration is read from AGENTSTACK_* environment variables with sensible defaults.
The Config singleton is initialized once and reused throughout the SDK lifecycle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    """Read an environment variable with a default."""
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = True) -> bool:
    """Read a boolean environment variable."""
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


def _env_int(key: str, default: int = 0) -> int:
    """Read an integer environment variable."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass(frozen=True)
class AgentStackConfig:
    """Immutable SDK configuration read from environment variables.

    Attributes:
        api_key: Authentication token for the Collector. Required for remote export.
        collector_url: URL of the Trace Collector endpoint.
        enabled: Master switch to enable/disable the SDK entirely.
        batch_size: Maximum number of spans to accumulate before flushing.
        export_interval_ms: Maximum milliseconds to wait before flushing a partial batch.
        max_queue_size: Maximum spans held in the in-memory ring buffer.
        log_level: Python logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        debug: Enable verbose stderr logging for SDK internals.
        service_name: Logical service/project name tagged on all spans.
    """

    api_key: str = ""
    collector_url: str = "http://localhost:4318"
    enabled: bool = True
    batch_size: int = 64
    export_interval_ms: int = 5000
    max_queue_size: int = 2048
    log_level: str = "INFO"
    debug: bool = False
    service_name: str = "default"
    project_id: str = "default"

    @classmethod
    def from_env(cls) -> AgentStackConfig:
        """Create a Config instance by reading AGENTSTACK_* environment variables.

        Environment Variables:
            AGENTSTACK_API_KEY: Required. API key for authentication.
            AGENTSTACK_COLLECTOR_URL: Default "http://localhost:4318".
            AGENTSTACK_ENABLED: Default "true". Set to "false" to disable.
            AGENTSTACK_BATCH_SIZE: Default 64. Max spans before flush.
            AGENTSTACK_EXPORT_INTERVAL: Default 5000. Milliseconds before flush.
            AGENTSTACK_MAX_QUEUE_SIZE: Default 2048. Ring buffer capacity.
            AGENTSTACK_LOG_LEVEL: Default "INFO". Python logging level.
            AGENTSTACK_DEBUG: Default "false". Enable verbose SDK logging.
            AGENTSTACK_SERVICE_NAME: Default "default". Service name for spans.
            AGENTSTACK_PROJECT_ID: Default "default". Project ID for the dashboard.
        """
        return cls(
            api_key=_env("AGENTSTACK_API_KEY", ""),
            collector_url=_env("AGENTSTACK_COLLECTOR_URL", "http://localhost:4318"),
            enabled=_env_bool("AGENTSTACK_ENABLED", True),
            batch_size=_env_int("AGENTSTACK_BATCH_SIZE", 64),
            export_interval_ms=_env_int("AGENTSTACK_EXPORT_INTERVAL", 5000),
            max_queue_size=_env_int("AGENTSTACK_MAX_QUEUE_SIZE", 2048),
            log_level=_env("AGENTSTACK_LOG_LEVEL", "INFO"),
            debug=_env_bool("AGENTSTACK_DEBUG", False),
            service_name=_env("AGENTSTACK_SERVICE_NAME", "default"),
            project_id=_env("AGENTSTACK_PROJECT_ID", "default"),
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_config: AgentStackConfig | None = None


def get_config() -> AgentStackConfig:
    """Return the global AgentStackConfig singleton (lazy-initialized from env)."""
    global _config
    if _config is None:
        _config = AgentStackConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset the global config singleton. Primarily useful for testing."""
    global _config
    _config = None
