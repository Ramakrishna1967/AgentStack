# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Pydantic v2 data models for AgentStack spans and traces.

These models define the canonical data shapes used throughout the SDK.
Field names and types align with the ClickHouse schema defined in the
project's ARCHITECTURE documentation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpanStatus(str, enum.Enum):
    """Status of a completed span."""

    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


class SpanEvent(BaseModel):
    """An event recorded during a span's lifetime.

    Events are discrete occurrences within a span, such as a log message,
    a streaming chunk arrival, or an exception.
    """

    name: str
    timestamp: int = Field(description="Wall-clock time in nanoseconds since epoch")
    attributes: dict[str, str] = Field(default_factory=dict)


class SpanModel(BaseModel):
    """Canonical Span data model matching the ClickHouse `spans` table schema.

    A Span represents a single unit of work within a Trace  an LLM call,
    a tool invocation, a memory read, or any @observe-decorated function.
    """

    trace_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID grouping all spans in one agent execution",
    )
    span_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this operation",
    )
    parent_span_id: str | None = Field(
        default=None,
        description="Parent span ID forming the tree structure",
    )
    name: str = Field(description="Operation name: llm.chat, tool.call, memory.read, etc.")
    start_time: int = Field(
        default=0,
        description="Wall-clock start time in nanoseconds since epoch",
    )
    end_time: int = Field(
        default=0,
        description="Wall-clock end time in nanoseconds since epoch",
    )
    duration_ms: int = Field(
        default=0,
        description="Computed duration in milliseconds",
    )
    status: SpanStatus = Field(default=SpanStatus.OK)
    service_name: str = Field(default="default")
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs: llm.model, llm.tokens.in, tool.name, etc.",
    )
    events: list[SpanEvent] = Field(default_factory=list)
    project_id: str = Field(default="")
    api_key_hash: str = Field(default="")

    def to_export_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary suitable for JSON export / transport."""
        return self.model_dump(mode="json")


class TraceModel(BaseModel):
    """A Trace is a collection of related Spans forming one agent execution.

    One user request = one Trace = a tree of Spans.
    """

    trace_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID for this trace",
    )
    spans: list[SpanModel] = Field(default_factory=list)
    start_time: int = Field(
        default=0,
        description="Earliest span start_time in the trace",
    )
    end_time: int = Field(
        default=0,
        description="Latest span end_time in the trace",
    )
    service_name: str = Field(default="default")
    status: SpanStatus = Field(default=SpanStatus.OK)

    @property
    def duration_ms(self) -> int:
        """Total trace duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) // 1_000_000
        return 0

    @property
    def span_count(self) -> int:
        """Number of spans in this trace."""
        return len(self.spans)

    @property
    def has_errors(self) -> bool:
        """True if any span in the trace has ERROR status."""
        return any(s.status == SpanStatus.ERROR for s in self.spans)
