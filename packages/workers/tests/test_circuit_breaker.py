# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for CircuitBreaker."""

import time

from workers.consumer import CircuitBreaker


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_single_failure_stays_closed(self):
        """Single failure should not open the circuit."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_threshold_opens_circuit(self):
        """Reaching failure threshold should open the circuit."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_success_resets_failure_count(self):
        """Success should reset failure count and keep circuit closed."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_recovery_timeout_allows_half_open(self):
        """After recovery timeout, circuit should enter HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        
        time.sleep(0.15)
        assert cb.can_execute() is True
        assert cb.state == "half_open"

    def test_half_open_success_closes_circuit(self):
        """Success in HALF_OPEN state should close the circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == "half_open"
        
        cb.record_success()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_half_open_failure_opens_circuit(self):
        """Failure in HALF_OPEN state should re-open the circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == "half_open"
        
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_half_open_max_attempts(self):
        """Should limit attempts in HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max=1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == "half_open"
        
        # First attempt allowed
        assert cb.can_execute() is True
        # After first attempt, no more allowed until success or timeout
        assert cb.can_execute() is False
