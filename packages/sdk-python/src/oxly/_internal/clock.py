# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Monotonic clock wrapper for accurate span timing.

Provides two clock sources:
- wall_clock_ns(): Wall-clock time (time.time_ns) for absolute timestamps
- monotonic_ns(): Monotonic clock (time.monotonic_ns) for duration measurement

The monotonic clock is immune to NTP adjustments and daylight saving changes,
making it reliable for measuring elapsed time between span start and end.
"""

import time


def wall_clock_ns() -> int:
    """Return current wall-clock time in nanoseconds since epoch.

    Used for span start_time and end_time fields that need absolute timestamps.
    """
    return time.time_ns()


def monotonic_ns() -> int:
    """Return monotonic clock value in nanoseconds.

    Used for accurate duration measurement. Not affected by system clock changes.
    """
    return time.monotonic_ns()


def duration_ms(start_mono_ns: int, end_mono_ns: int) -> int:
    """Compute duration in milliseconds from two monotonic nanosecond timestamps.

    Args:
        start_mono_ns: Monotonic nanosecond timestamp at span start.
        end_mono_ns: Monotonic nanosecond timestamp at span end.

    Returns:
        Duration in milliseconds (integer, floored).
    """
    return (end_mono_ns - start_mono_ns) // 1_000_000
