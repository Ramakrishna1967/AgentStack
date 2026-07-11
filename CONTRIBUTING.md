# Contributing to Oxly

## Getting Started

1. Fork the repo and create a branch from `main`
2. Install dependencies (see README)
3. Make your changes
4. Run tests and linting
5. Open a pull request

## Development Setup

```bash
# SDK
pip install -e ./packages/sdk-python

# API
pip install -e ./packages/api

# Dashboard
cd packages/dashboard && npm ci
```

## Running Tests

```bash
# Python
pytest packages/

# Dashboard
cd packages/dashboard && npm test
```

## Code Style

- Python: `flake8` + `mypy --ignore-missing-imports`
- TypeScript: `eslint` + `tsc`
- No unused imports, no commented-out code

## Pull Request Guidelines

- One feature or fix per PR
- Include a clear description of what and why
- Tests are required for new features
- Security-sensitive changes require two reviewer approvals

## Reporting Bugs

Open a GitHub issue with:
- Oxly version
- Python version
- Minimal reproduction steps
- Expected vs actual behavior

For security issues, see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree your contributions will be licensed under Apache 2.0.
