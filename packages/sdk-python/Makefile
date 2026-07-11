# AgentStack SDK — Makefile
# Development commands for the Python SDK

.PHONY: help install install-dev test test-cov lint format clean build

help:
	@echo "AgentStack SDK Development Commands"
	@echo "===================================="
	@echo "install       Install package in editable mode"
	@echo "install-dev   Install with dev dependencies"
	@echo "test          Run all tests with pytest"
	@echo "test-cov      Run tests with coverage report"
	@echo "lint          Run ruff linter"
	@echo "format        Format code with ruff"
	@echo "clean         Remove build artifacts and caches"
	@echo "build         Build the package distribution"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/agentstack --cov-report=term-missing --cov-report=html

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".oxly.db" -delete

build:
	python -m build
