# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for the public `import oxly` / `from oxly import observe` entry point.

Distinct from test_decorator.py, which imports `oxly.decorator.observe`
directly. A prior bug in oxly/__init__.py hand-wrote a wrapper around the
real decorator that only forwarded `func`/`name`, silently dropping
`capture_args`/`capture_result` -- exactly the documented usage in the
README quickstart. No test exercised this public path, which is how it
stayed hidden.
"""

import oxly
from oxly import observe


def test_public_observe_supports_capture_args_kwarg():
    @observe(capture_args=False)
    def add(x, y):
        return x + y

    assert add(3, 4) == 7


def test_public_observe_supports_capture_result_kwarg():
    @observe(capture_result=False)
    def multiply(x, y):
        return x * y

    assert multiply(5, 6) == 30


def test_public_observe_supports_all_documented_kwargs_together():
    @observe(name="custom.op", capture_args=False, capture_result=False)
    def subtract(x, y):
        return x - y

    assert subtract(10, 3) == 7


def test_oxly_dot_observe_matches_module_attribute():
    """`oxly.observe` (README's other documented style) is the same function."""
    assert oxly.observe is observe
