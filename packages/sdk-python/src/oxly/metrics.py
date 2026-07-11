# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""SDK metrics collection for observability of the observability platform.

Tracks key operational metrics so users and operators can monitor
the health of the SDK's internal data pipeline:

- Spans created, exported, dropped
- Export latency and retry counts
- Buffer utilization
- Sanitization stats

All counters are thread-safe using atomic operations.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class SDKMetrics:
    """Thread-safe metrics collector for the Oxly SDK.

    All fields use simple atomic counters for thread safety.
    Call snapshot() to get a consistent point-in-time view.
    """

    _lock: threading.Lock = field(default_factory=threading.Lock)

    # Span lifecycle
    spans_created: int = 0
    spans_exported: int = 0
    spans_dropped: int = 0
    spans_failed: int = 0

    # Export pipeline
    export_attempts: int = 0
    export_successes: int = 0
    export_failures: int = 0
    export_retries: int = 0
    export_latency_ms_total: float = 0.0
    export_latency_ms_max: float = 0.0

    # Buffer
    buffer_current_size: int = 0
    buffer_capacity: int = 0
    buffer_overflow_count: int = 0

    # Sanitization
    pii_fields_redacted: int = 0
    pii_spans_sanitized: int = 0

    # Local store fallback
    local_store_saves: int = 0
    local_store_retrievals: int = 0
    local_store_errors: int = 0

    # Timing
    _last_export_time: float = 0.0

    def increment(self, name: str, count: int = 1) -> None:
        """Atomically increment a metric counter."""
        with self._lock:
            current = getattr(self, name, None)
            if current is not None and isinstance(current, (int, float)):
                setattr(self, name, current + count)

    def record_export(self, span_count: int, latency_ms: float, success: bool) -> None:
        """Record an export attempt with timing."""
        with self._lock:
            self.export_attempts += 1
            if success:
                self.export_successes += 1
                self.spans_exported += span_count
                self.export_latency_ms_total += latency_ms
                self.export_latency_ms_max = max(self.export_latency_ms_max, latency_ms)
                self._last_export_time = time.monotonic()
            else:
                self.export_failures += 1
                self.spans_failed += span_count

    def record_buffer_state(self, current_size: int, capacity: int, overflow: bool) -> None:
        """Record buffer state snapshot."""
        with self._lock:
            self.buffer_current_size = current_size
            self.buffer_capacity = capacity
            if overflow:
                self.buffer_overflow_count += 1
                self.spans_dropped += 1

    def snapshot(self) -> dict[str, int | float]:
        """Get a point-in-time snapshot of all metrics."""
        with self._lock:
            avg_latency = (
                self.export_latency_ms_total / self.export_successes
                if self.export_successes > 0
                else 0.0
            )
            return {
                "spans_created": self.spans_created,
                "spans_exported": self.spans_exported,
                "spans_dropped": self.spans_dropped,
                "spans_failed": self.spans_failed,
                "export_attempts": self.export_attempts,
                "export_successes": self.export_successes,
                "export_failures": self.export_failures,
                "export_retries": self.export_retries,
                "export_latency_ms_avg": round(avg_latency, 2),
                "export_latency_ms_max": round(self.export_latency_ms_max, 2),
                "buffer_utilization_pct": round(
                    (self.buffer_current_size / self.buffer_capacity * 100)
                    if self.buffer_capacity > 0
                    else 0.0,
                    1,
                ),
                "buffer_overflow_count": self.buffer_overflow_count,
                "pii_fields_redacted": self.pii_fields_redacted,
                "pii_spans_sanitized": self.pii_spans_sanitized,
                "local_store_saves": self.local_store_saves,
                "local_store_errors": self.local_store_errors,
                "last_export_ago_s": round(
                    time.monotonic() - self._last_export_time
                    if self._last_export_time > 0
                    else -1.0,
                    2,
                ),
            }


# Global singleton
_metrics = SDKMetrics()


def get_metrics() -> SDKMetrics:
    """Get the global SDK metrics instance."""
    return _metrics
