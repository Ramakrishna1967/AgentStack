# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""Oxly SDK  Chrome DevTools for AI Agents.

Provides observability for AI Agents built on LangGraph, CrewAI, AutoGen,
and custom Python implementations.

Quick Start:
    from oxly import observe

    @observe
    def my_agent(query: str) -> str:
        result = llm.chat(query)
        return result

Public API:
    - observe: Decorator to instrument functions (sync + async)
    - init: Initialize the SDK with custom configuration
    - Tracer: Low-level tracer for manual span creation
    - Span: Individual span representing a unit of work
"""

from __future__ import annotations

__version__ = "0.1.0a1"
__all__ = [
    "observe",
    "init",
    "Tracer",
    "Span",
    "__version__",
]

import logging
from typing import TYPE_CHECKING

from oxly.config import OxlyConfig, get_config, reset_config
from oxly.tracer import Span, Tracer

# Lazy import to avoid circular dependency  decorator is built in Step 2
# For now, provide a placeholder that gets replaced on first access.
_observe_func = None


def observe(func=None, *, name: str | None = None):
    """Decorator to instrument a function for observability.

    Creates a Span for each function call, capturing arguments, return values,
    exceptions, and timing. Works on both sync and async functions.

    Usage:
        @observe
        def my_function(x):
            return x * 2

        @observe(name="custom_name")
        async def my_async_function(x):
            return await some_async_call(x)

    Args:
        func: The function to decorate (when used without parentheses).
        name: Optional custom span name. Defaults to the function's __name__.
    """
    try:
        from oxly.decorator import observe as _obs

        return _obs(func, name=name)
    except ImportError:
        # decorator.py not yet created (Step 2)  return function unmodified
        if func is not None:
            return func
        # Called with arguments: @observe(name="x")  return identity decorator
        def _identity(f):
            return f
        return _identity


def init(
    *,
    api_key: str | None = None,
    collector_url: str | None = None,
    enabled: bool | None = None,
    service_name: str | None = None,
    debug: bool | None = None,
    auto_instrument: bool = True,
) -> None:
    """Initialize the Oxly SDK with custom configuration.

    Any provided arguments override the corresponding OXLY_* environment
    variables. Call this before any @observe decorators execute.

    Args:
        api_key: API key for the Collector (overrides OXLY_API_KEY).
        collector_url: Collector URL (overrides OXLY_COLLECTOR_URL).
        enabled: Enable/disable the SDK (overrides OXLY_ENABLED).
        service_name: Service name for spans (overrides OXLY_SERVICE_NAME).
        debug: Enable debug logging (overrides OXLY_DEBUG).
    """
    import os

    if api_key is not None:
        os.environ["OXLY_API_KEY"] = api_key
    if collector_url is not None:
        os.environ["OXLY_COLLECTOR_URL"] = collector_url
    if enabled is not None:
        os.environ["OXLY_ENABLED"] = str(enabled).lower()
    if service_name is not None:
        os.environ["OXLY_SERVICE_NAME"] = service_name
    if debug is not None:
        os.environ["OXLY_DEBUG"] = str(debug).lower()

    # Apply auto-instrumentation if requested
    if auto_instrument:
        try:
            from oxly.frameworks import auto_instrument as perform_auto_instrument
            perform_auto_instrument()
        except ImportError:
            pass # Frameworks not available in this build step

    # Reset singletons so they pick up new env vars
    reset_config()
    Tracer.reset()

    # Configure logging
    config = get_config()
    log_level = logging.DEBUG if config.debug else getattr(logging, config.log_level, logging.INFO)
    logging.getLogger("oxly").setLevel(log_level)

    if config.debug:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[oxly] %(levelname)s %(name)s: %(message)s")
        )
        oxly_logger = logging.getLogger("oxly")
        if not oxly_logger.handlers:
            oxly_logger.addHandler(handler)
