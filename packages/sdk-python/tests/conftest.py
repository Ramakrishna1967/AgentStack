# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Shared pytest fixtures for AgentStack SDK tests."""

import os
import tempfile
from pathlib import Path

import pytest

from oxly.config import reset_config
from oxly.context import clear_context
from oxly.exporter import reset_processor
from oxly.local_store import LocalStore, reset_local_store
from oxly.models import SpanModel, SpanStatus
from oxly.tracer import Tracer


@pytest.fixture(autouse=True)
def reset_sdk():
    """Reset all SDK singletons before each test."""
    clear_context()
    Tracer.reset()
    reset_config()
    reset_processor()
    reset_local_store()
    # Clear env vars
    for key in list(os.environ.keys()):
        if key.startswith("OXLY_"):
            del os.environ[key]
    yield
    # Cleanup after test
    clear_context()
    Tracer.reset()
    reset_config()
    reset_processor()
    reset_local_store()


@pytest.fixture
def temp_db():
    """Provide a temporary SQLite database file."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        yield str(db_path)


@pytest.fixture
def local_store(temp_db):
    """Provide a LocalStore instance with a temp database."""
    return LocalStore(db_path=temp_db)


@pytest.fixture
def mock_span():
    """Provide a sample SpanModel for testing."""
    return SpanModel(
        name="test.span",
        start_time=1000000000,
        end_time=2000000000,
        duration_ms=1000,
        status=SpanStatus.OK,
        service_name="test-service",
        attributes={
            "test.key": "test.value",
            "llm.model": "gpt-4",
        },
    )


@pytest.fixture
def mock_spans():
    """Provide a list of sample SpanModels."""
    return [
        SpanModel(name=f"test.span.{i}", duration_ms=i * 100)
        for i in range(5)
    ]


@pytest.fixture
def env_config():
    """Set up test environment variables."""
    os.environ.update({
        "OXLY_API_KEY": "test-api-key",
        "OXLY_COLLECTOR_URL": "http://localhost:4318",
        "OXLY_ENABLED": "true",
        "OXLY_BATCH_SIZE": "32",
        "OXLY_EXPORT_INTERVAL": "1000",
        "OXLY_SERVICE_NAME": "test-service",
    })
    reset_config()
    yield
    # Clean up
    for key in list(os.environ.keys()):
        if key.startswith("OXLY_"):
            del os.environ[key]
    reset_config()
